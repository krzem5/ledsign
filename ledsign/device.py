from collections.abc import Callable
from ledsign.hardware import LEDSignHardware
from ledsign.program import LEDSignProgram
from ledsign.program_io import LEDSignCompiledProgram
from ledsign.protocol import LEDSignProtocol
import time



__all__=["LEDSignDeviceNotFoundError","LEDSignAccessError","LEDSign"]



class LEDSignDeviceNotFoundError(Exception):
	"""
	Raised by :py:func:`LEDSign.open` when no device was found.
	"""



class LEDSignAccessError(Exception):
	"""
	Raised when the device access mode was violated.
	"""



class LEDSign(object):
	"""
	Returned by :py:func:`LEDSign.open`, represents a handle to an LED sign device.

	.. autoattribute:: ACCESS_MODE_NONE
	   :no-value:

	   Access mode representing a device handle without read or write access. At the moment only used by closed device handles.

	.. autoattribute:: ACCESS_MODE_READ
	   :no-value:

	   Access mode representing a device handle with only read permissions.

	.. autoattribute:: ACCESS_MODE_READ_WRITE
	   :no-value:

	   Access mode representing a device handle with both read and write permissions.
	"""

	ACCESS_MODE_NONE:int=0x00
	ACCESS_MODE_READ:int=0x01
	ACCESS_MODE_READ_WRITE:int=0x02

	ACCESS_MODES:dict[int,str]={
		ACCESS_MODE_NONE: "none",
		ACCESS_MODE_READ: "read-only",
		ACCESS_MODE_READ_WRITE: "read-write",
	}

	__slots__=["__weakref__","_path","_handle","_access_mode","_psu_current","_storage_size","_hardware","_firmware","_serial_number","_driver_brightness","_driver_program_paused","_driver_temperature","_driver_load","_driver_program_time","_driver_current_usage","_driver_program_offset_divisor","_driver_info_sync_next_time","_driver_info_sync_interval","_program"]

	def __init__(self,path,handle,config_packet) -> None:
		self._path=path
		self._handle=handle
		self._access_mode=config_packet[6]&0x0f
		self._psu_current=(config_packet[7]&0x7f)/10
		self._storage_size=config_packet[1]<<10
		self._hardware=LEDSignHardware(handle,config_packet[2])
		self._firmware=config_packet[9].hex()
		self._serial_number=config_packet[10]
		self._driver_brightness=config_packet[5]&0x0f
		self._driver_program_paused=not (config_packet[8]&1)
		self._driver_program_offset_divisor=max((config_packet[3]&0xff)<<1,1)*60
		self._driver_info_sync_next_time=0
		self._driver_info_sync_interval=0.5
		self._program=LEDSignProgram._create_unloaded_from_device(self,config_packet[3],config_packet[4])

	def __del__(self) -> None:
		if (self._handle is not None):
			LEDSignProtocol.close(self._handle)

	def __repr__(self) -> str:
		return f"<LEDSign id={self._serial_number:016x} fw={self._firmware}>"

	def _check_if_closed(self) -> None:
		if (self._handle is not None):
			return
		raise LEDSignAccessError("Device handle was closed, no access allowed")

	def _sync_driver_info(self) -> None:
		self._check_if_closed()
		if (time.time()<self._driver_info_sync_next_time):
			return
		driver_status=LEDSignProtocol.process_packet(self._handle,LEDSignProtocol.PACKET_TYPE_LED_DRIVER_STATUS_RESPONSE,LEDSignProtocol.PACKET_TYPE_LED_DRIVER_STATUS_REQUEST)
		self._driver_temperature=437.226612-driver_status[0]*0.468137
		self._driver_load=driver_status[1]/160
		self._driver_program_time=driver_status[2]/self._driver_program_offset_divisor
		self._driver_current_usage=driver_status[3]*1e-6
		self._driver_info_sync_next_time=time.time()+self._driver_info_sync_interval

	def close(self) -> None:
		"""
		Closes the underlying device handle. After a call to this function, all methods except for :py:func:`get_path` and :py:func:`get_access_mode` will raise a :py:exc:`LEDSignAccessError` exception.
		"""
		self._check_if_closed()
		LEDSignProtocol.close(self._handle)
		self._handle=None
		self._path=None
		self._access_mode=LEDSign.ACCESS_MODE_NONE

	def get_path(self) -> str|None:
		"""
		Returns the underlying OS path of the device, or :python:`None` if the device was closed.
		"""
		return self._path

	def get_access_mode(self) -> int:
		"""
		Returns the access mode (permissions) granted by the device. Possible return values are:

		* :py:attr:`ACCESS_MODE_NONE`: No access; device handle was closed
		* :py:attr:`ACCESS_MODE_READ`: Read-only access; program uploads will be rejected
		* :py:attr:`ACCESS_MODE_READ_WRITE`: Full read-write access
		"""
		return self._access_mode

	def get_access_mode_str(self) -> str:
		"""
		Same as :py:func:`get_access_mode`, but returns a stringified versions of the access mode. Possible values are: :python:`"none"`, :python:`"read-only"`, or :python:`"read-write"`.
		"""
		return LEDSign.ACCESS_MODES[self._access_mode]

	def get_psu_current(self) -> float:
		"""
		Returns the configured theoretical current limit of the power supply, in amps. As only 5V power supplies are supported, no explicit voltage getter method is provided.

		.. danger::
		   If the device draws more current than this limit, a device-internal overcurrent safety flag will be raised. Whenever this flag is active, no changes made to the device will be visible.

		   **For safety reasons, this flag can only be cleared from the UI menu, or through device reboots.**
		"""
		self._check_if_closed()
		return self._psu_current

	def get_storage_size(self) -> int:
		"""
		Returns the storage capacity of the device allocated for program storage, in bytes.
		"""
		self._check_if_closed()
		return self._storage_size

	def get_hardware(self) -> LEDSignHardware:
		"""
		Returns a read-only :py:class:`LEDSignHardware` object representing the current external hardware configuration of the device.
		"""
		self._check_if_closed()
		return self._hardware

	def get_firmware(self) -> str:
		"""
		Returns a 40-character hex string uniquely identifying the current firmware versions of the device.
		"""
		self._check_if_closed()
		return self._firmware

	def get_serial_number(self) -> int:
		"""
		Returns the unique 64-bit serial number of the device.
		"""
		self._check_if_closed()
		return self._serial_number

	def get_serial_number_str(self) -> str:
		"""
		Same as :py:func:`get_serial_number`, but formats the serial number as a 16-hex-digit string.
		"""
		self._check_if_closed()
		return f"{self._serial_number:016x}"

	def get_driver_brightness(self) -> float:
		"""
		Returns the current device brightness setting, normalized between :python:`0.0` and :python:`1.0`.

		.. note::
		   If the overcurrent flag was tripped (see :py:func:`get_psu_current` for details), the returned brightness setting may not reflect the real-world conditions.
		"""
		self._check_if_closed()
		return round(self._driver_brightness*20/7)/20

	def is_driver_paused(self) -> bool:
		"""
		Returns :python:`True` if the LED driver is in a paused state (ie. the program playback is frozen), and :python:`False` otherwise.

		.. note::
		   For internal protocol reasons, this flag is **not** periodically synchronized with the device.
		"""
		self._check_if_closed()
		return self._driver_program_paused

	def get_driver_temperature(self) -> float:
		"""
		Returns the current temperature of the LED driver, in degrees Celsius.

		The temperature is fetched periodically from the device, at an interval specified by :py:func:`get_driver_status_reload_time`.
		"""
		self._sync_driver_info()
		return self._driver_temperature

	def get_driver_load(self) -> float:
		"""
		Returns the current driver CPU load, normalized between :python:`0.0` and :python:`1.0`. The returned value represents the frame render duration, measured as a fraction of the overall frame time.

		The driver load is fetched periodically from the device, at an interval specified by :py:func:`get_driver_status_reload_time`.
		"""
		self._sync_driver_info()
		return self._driver_load

	def get_driver_program_time(self) -> float:
		"""
		Returns the current program timestamp. The timestamp wraps around to zero at program duration, ie. :python:`timestamp %= self.get_program().get_duration()`.

		The timestamp is fetched periodically from the device, at an interval specified by :py:func:`get_driver_status_reload_time`.
		"""
		self._sync_driver_info()
		return self._driver_program_time

	def get_driver_current_usage(self) -> float:
		"""
		Returns the current being drawn by the device hardware from the power supply. Internally, this same value is used in the overcurrent protection circuit (see :py:func:`get_psu_current` for more details).

		The current usage is fetched periodically from the device, at an interval specified by :py:func:`get_driver_status_reload_time`.
		"""
		self._sync_driver_info()
		return self._driver_current_usage

	def get_driver_status_reload_time(self) -> float:
		"""
		Returns the current refresh interval (in seconds) used for fetching driver data, or :python:`-1` if caching is disabled. Can be modified using :py:func:`set_driver_status_reload_time`.
		"""
		self._check_if_closed()
		return self._driver_info_sync_interval

	def set_driver_status_reload_time(self,interval:float) -> float:
		"""
		Sets :python:`interval` as the new driver data refresh interval (in seconds), and returns the previous value. Negative values for :python:`interval` disable caching and fetch data whenever it is requested.
		"""
		self._check_if_closed()
		out=self._driver_info_sync_interval
		self._driver_info_sync_interval=(-1 if interval<=0 else interval)
		self._driver_info_sync_next_time+=self._driver_info_sync_interval-out
		return out

	def get_program(self) -> LEDSignProgram:
		"""
		Returns a read-only :py:class:`LEDSignProgram` object containing the current device program. For performance reasons, the program is lazily loaded only when its keypoints are accessed to prevent significant start-up delays.
		"""
		self._check_if_closed()
		return self._program

	def upload_program(self,program:LEDSignCompiledProgram,callback:Callable[[float,bool],None]|None=None) -> None:
		"""
		Uploads the given :python:`program` to the device. If the device was opened in read-only mode, a :py:exc:`LEDSignAccessError` exception will be raised.

		The optional :python:`callback` argument is periodically called throughout the upload process with arguments :python:`(progress, is_first_stage)`.
		"""
		if (not isinstance(program,LEDSignCompiledProgram)):
			raise TypeError(f"Expected 'LEDSignCompiledProgram', got '{program.__class__.__name__}'")
		if (callback is not None and not callable(callback)):
			raise TypeError(f"Expected 'function', got '{callback.__class__.__name__}'")
		if (self._access_mode!=LEDSign.ACCESS_MODE_READ_WRITE):
			raise LEDSignAccessError("Program upload not allowed, Python API configured as read-only")
		program._upload_to_device(self,callback)

	@staticmethod
	def open(path:str|None=None) -> "LEDSign":
		"""
		Opens the device pointed to by :python:`path` (or the default device if no path is provided), and returns its corresponding :py:class:`LEDSign` object. The device path must have been returned by a previous call to :py:func:`enumerate`.

		If the device is already in use by a different program, a :py:exc:`LEDSignDeviceInUseError` will be raised. Additionally, if the device protocol version is incompatible, or if the Python API was disabled in device settings, a :py:exc:`LEDSignUnsupportedProtocolError` or :py:exc:`LEDSignProtocolError` exception will be returned respectively.

		.. note::
		   Due to the internal USB-level configuration, this library can be used alongside the UI without triggering a :py:exc:`LEDSignDeviceInUseError` exception. This feature allows the UI to be kept open while writing new programs to ease the debugging process.
		"""
		if (path is None):
			devices=LEDSignProtocol.enumerate()
			if (not devices):
				raise LEDSignDeviceNotFoundError("No device found")
			path=devices[0]
		if (not isinstance(path,str)):
			raise TypeError(f"Expected 'str', got '{path.__class__.__name__}'")
		handle=None
		try:
			handle=LEDSignProtocol.open(path)
			config_packet=LEDSignProtocol.process_packet(handle,LEDSignProtocol.PACKET_TYPE_DEVICE_INFO,LEDSignProtocol.PACKET_TYPE_HOST_INFO,LEDSignProtocol.VERSION)
		except Exception as e:
			if (handle is not None):
				LEDSignProtocol.close(handle)
			raise e
		return LEDSign(path,handle,config_packet)

	@staticmethod
	def enumerate() -> list[str]:
		"""
		Returns a list of available device paths detected by the OS.
		"""
		return LEDSignProtocol.enumerate()
