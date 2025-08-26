from ledsign.hardware import LEDSignHardware
from ledsign.program import LEDSignProgram
from ledsign.program_io import LEDSignCompiledProgram
from ledsign.protocol import LEDSignProtocol
import time



__all__=["LEDSignDeviceNotFoundError","LEDSignAccessError","LEDSign"]



LEDSignDeviceNotFoundError=type("LEDSignDeviceNotFoundError",(Exception,),{})
LEDSignAccessError=type("LEDSignAccessError",(Exception,),{})



class LEDSign(object):
	ACCESS_MODE_NONE=0x00
	ACCESS_MODE_READ=0x01
	ACCESS_MODE_READ_WRITE=0x02

	ACCESS_MODES={
		ACCESS_MODE_NONE: "none",
		ACCESS_MODE_READ: "read-only",
		ACCESS_MODE_READ_WRITE: "read-write",
	}

	__slots__=["__weakref__","path","_handle","_access_mode","_psu_current","_storage_size","_hardware","_firmware","_serial_number","_driver_brightness","_driver_program_paused","_driver_temperature","_driver_load","_driver_program_time","_driver_current_usage","_driver_program_offset_divisor","_driver_program_max_offset","_driver_info_sync_next_time","_driver_info_sync_interval","_program"]

	def __init__(self,path,handle,config_packet):
		self.path=path
		self._handle=handle
		self._access_mode=config_packet[6]&0x0f
		self._psu_current=config_packet[7]/10
		self._storage_size=config_packet[1]<<10
		self._hardware=LEDSignHardware(handle,config_packet[2])
		self._firmware=config_packet[9].decode("utf-8")
		self._serial_number=config_packet[10]
		self._driver_brightness=config_packet[5]&0x0f
		self._driver_program_paused=not config_packet[8]
		self._driver_program_offset_divisor=max((config_packet[3]&0xff)<<1,1)*60
		self._driver_program_max_offset=max(config_packet[3]>>8,1)
		self._driver_info_sync_next_time=0
		self._driver_info_sync_interval=0.5
		self._program=LEDSignProgram._create_unloaded_from_device(self,config_packet[3],config_packet[4])

	def __del__(self):
		self.close()

	def __repr__(self):
		return f"<LEDSign id={self._serial_number:016x} fw={self._firmware}>"

	def _sync_driver_info(self):
		if (time.time()<self._driver_info_sync_next_time):
			return
		driver_status=LEDSignProtocol.process_packet(self._handle,LEDSignProtocol.PACKET_TYPE_LED_DRIVER_STATUS_RESPONSE,LEDSignProtocol.PACKET_TYPE_LED_DRIVER_STATUS_REQUEST)
		self._driver_temperature=437.226612-driver_status[0]*0.468137
		self._driver_load=driver_status[1]/160
		self._driver_program_time=driver_status[2]/self._driver_program_offset_divisor
		self._driver_current_usage=driver_status[3]*1e-6
		self._driver_info_sync_next_time=time.time()+self._driver_info_sync_interval

	def close(self):
		if (self._handle is not None):
			LEDSignProtocol.close(self._handle)
		self._handle=None

	def get_access_mode(self):
		return self._access_mode

	def get_psu_current(self):
		return self._psu_current

	def get_storage_size(self):
		return self._storage_size

	def get_hardware(self):
		return self._hardware

	def get_firmware(self):
		return self._firmware

	def get_raw_serial_number(self):
		return self._serial_number

	def get_serial_number(self):
		return f"{self._serial_number:016x}"

	def get_driver_brightness(self):
		return self._driver_brightness/8

	def is_driver_paused(self):
		return self._driver_program_paused

	def get_driver_temperature(self):
		self._sync_driver_info()
		return self._driver_temperature

	def get_driver_load(self):
		self._sync_driver_info()
		return self._driver_load

	def get_driver_program_time(self):
		self._sync_driver_info()
		return self._driver_program_time

	def get_driver_current_usage(self):
		self._sync_driver_info()
		return self._driver_current_usage

	def get_driver_program_duration(self):
		return self._driver_program_max_offset/self._driver_program_offset_divisor

	def get_driver_status_reload_time(self):
		return self._driver_info_sync_interval

	def set_driver_status_reload_time(self,delta):
		self._driver_info_sync_interval=delta

	def get_program(self):
		return self._program

	def upload_program(self,program):
		if (not isinstance(program,LEDSignCompiledProgram)):
			raise TypeError(f"Expected 'LEDSignCompiledProgram', got '{program.__class__.__name__}'")
		if (self._access_mode!=LEDSign.ACCESS_MODE_READ_WRITE):
			raise LEDSignAccessError("Program upload not allowed, Python API configured as read-only")
		program._upload_to_device(self)

	@staticmethod
	def open(path=None):
		if (path is None):
			devices=LEDSignProtocol.enumerate()
			if (not devices):
				raise LEDSignDeviceNotFoundError("Device not found")
			path=devices[0]
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
	def enumerate():
		return LEDSignProtocol.enumerate()
