from collections.abc import Callable
from ledsign.hardware import LEDSignHardware
from ledsign.program import LEDSignProgram
from ledsign.program_io import LEDSignCompiledProgram
from ledsign.protocol import LEDSignProtocol
import time



__all__=["LEDSignDeviceNotFoundError","LEDSignAccessError","LEDSign"]



LEDSignDeviceNotFoundError=type("LEDSignDeviceNotFoundError",(Exception,),{})
LEDSignAccessError=type("LEDSignAccessError",(Exception,),{})



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

	__slots__=["__weakref__","_path","_handle","_access_mode","_psu_current","_storage_size","_hardware","_firmware","_serial_number","_driver_brightness","_driver_program_paused","_driver_temperature","_driver_load","_driver_program_time","_driver_current_usage","_driver_program_offset_divisor","_driver_program_max_offset","_driver_info_sync_next_time","_driver_info_sync_interval","_program"]

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
		self._driver_program_max_offset=max(config_packet[3]>>8,1)
		self._driver_info_sync_next_time=0
		self._driver_info_sync_interval=0.5
		self._program=LEDSignProgram._create_unloaded_from_device(self,config_packet[3],config_packet[4])

	def __del__(self) -> None:
		self.close()

	def __repr__(self) -> str:
		return f"<LEDSign id={self._serial_number:016x} fw={self._firmware}>"

	def _check_if_closed(self) -> None:
		if (self._handle is not None):
			return
		raise LEDSignProtocolError("Device handle closed")

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
		Closes the underlying device handle. After a call to this function, all other methods will raise an :py:exc:`LEDSignProtocolError`.
		"""
		if (self._handle is not None):
			LEDSignProtocol.close(self._handle)
		self._handle=None
		self._path=None
		self._access_mode=LEDSign.ACCESS_MODE_NONE

	def get_path(self) -> str|None:
		"""
		Returns the underlying OS path of the device, or :code:`None` if the device was closed.
		"""
		return self._path

	def get_access_mode(self) -> int:
		"""
		Returns the access mode (permissions) granted by the device. Possible return values are:

		* :py:attr:`ledsign.LEDSign.ACCESS_MODE_NONE`: No access; device handle was closed
		* :py:attr:`ledsign.LEDSign.ACCESS_MODE_READ`: Read-only access; program uploads will be rejected
		* :py:attr:`ledsign.LEDSign.ACCESS_MODE_READ_WRITE`: Full read-write access
		"""
		return self._access_mode

	def get_access_mode_str(self) -> str:
		"""
		Same as :py:func:`get_access_mode`, but returns a stringified versions of the access mode. Possible values are: :code:`"none"`, :code:`"read-only"`, or :code:`"read-write"`.
		"""
		return LEDSign.ACCESS_MODES[self._access_mode]

	def get_psu_current(self) -> float:
		"""
		Returns the configured theoretical current limit of the power supply, in Amps. As only 5V power supplies are supported, no explicit voltage getter method is provided.

		.. danger::
		   If the device draws more current than this limit, a device-internal overcurrent safety flag will be raised. Whenever this flag is active, no changes will be visible on the device.

		   **For safety reasons, this flag can only be cleared from the UI menu.**
		"""
		self._check_if_closed()
		return self._psu_current

	def get_storage_size(self) -> int:
		"""
		:func:`get_storage_size`
		"""
		self._check_if_closed()
		return self._storage_size

	def get_hardware(self) -> LEDSignHardware:
		"""
		:func:`get_hardware`
		"""
		self._check_if_closed()
		return self._hardware

	def get_firmware(self) -> str:
		"""
		:func:`get_firmware`
		"""
		self._check_if_closed()
		return self._firmware

	def get_raw_serial_number(self) -> int:
		"""
		:func:`get_raw_serial_number`
		"""
		self._check_if_closed()
		return self._serial_number

	def get_serial_number(self) -> str:
		"""
		:func:`get_serial_number`
		"""
		self._check_if_closed()
		return f"{self._serial_number:016x}"

	def get_driver_brightness(self) -> float:
		"""
		:func:`get_driver_brightness`
		"""
		self._check_if_closed()
		return round(self._driver_brightness*20/7)/20

	def is_driver_paused(self) -> bool:
		"""
		:func:`is_driver_paused`
		"""
		self._check_if_closed()
		return self._driver_program_paused

	def get_driver_temperature(self) -> float:
		"""
		:func:`get_driver_temperature`
		"""
		self._sync_driver_info()
		return self._driver_temperature

	def get_driver_load(self) -> float:
		"""
		:func:`get_driver_load`
		"""
		self._sync_driver_info()
		return self._driver_load

	def get_driver_program_time(self) -> float:
		"""
		:func:`get_driver_program_time`
		"""
		self._sync_driver_info()
		return self._driver_program_time

	def get_driver_current_usage(self) -> float:
		"""
		:func:`get_driver_current_usage`
		"""
		self._sync_driver_info()
		return self._driver_current_usage

	def get_driver_program_duration(self) -> float:
		"""
		:func:`get_driver_program_duration`
		"""
		return self._driver_program_max_offset/self._driver_program_offset_divisor

	def get_driver_status_reload_time(self):
		"""
		:func:`get_driver_status_reload_time`
		"""
		return self._driver_info_sync_interval

	def set_driver_status_reload_time(self,delta:float) -> float:
		"""
		:func:`set_driver_status_reload_time`
		"""
		out=self._driver_info_sync_interval
		self._driver_info_sync_interval=delta
		return out

	def get_program(self) -> LEDSignProgram:
		"""
		:func:`get_program`
		"""
		return self._program

	def upload_program(self,program:LEDSignCompiledProgram,callback:Callable[[float,bool],None]|None=None) -> None:
		"""
		:func:`upload_program`
		"""
		if (not isinstance(program,LEDSignCompiledProgram)):
			raise TypeError(f"Expected 'LEDSignCompiledProgram', got '{program.__class__.__name__}'")
		if (self._access_mode!=LEDSign.ACCESS_MODE_READ_WRITE):
			raise LEDSignAccessError("Program upload not allowed, Python API configured as read-only")
		program._upload_to_device(self,callback)

	@staticmethod
	def open(path:str|None=None) -> "LEDSign":
		"""
		:func:`open`
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
		:func:`enumerate`
		"""
		return LEDSignProtocol.enumerate()
