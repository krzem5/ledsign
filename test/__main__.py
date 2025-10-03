from ledsign import *
from ledsign.protocol import LEDSignProtocol
import random
import struct
import sys



class TestManager(object):
	_instance=None

	def __init__(self):
		self._functions=[]
		self._success_count=0
		self._fail_count=0
		return

	def __call__(self,fn):
		self._functions.append(fn)
		return fn

	def execute(self):
		TestManager._instance=self
		for fn in self._functions:
			fn()
		TestManager._instance=None
		print(self._success_count,self._fail_count)

	def equal(self,a,b):
		if (a.__class__==b.__class__ and (a==b or (isinstance(a,float) and isinstance(b,float) and abs(a-b)<1e-6))):
			self._success_count+=1
			return True
		return self.fail("Objects not equal",2)

	def exception(self,fn,exception):
		try:
			fn()
			return self.fail("Expected exception",2)
		except Exception as e:
			if (not isinstance(e,exception)):
				self.fail("Wrong exception raised",2)
				raise e
		self._success_count+=1
		return True

	def fail(self,reason,outer_frame_index=1):
		frame=sys._getframe(outer_frame_index)
		print(f"{frame.f_code.co_filename}:{frame.f_lineno}({frame.f_code.co_name}): {reason}")
		self._fail_count+=1
		return False

	@staticmethod
	def instance():
		return TestManager._instance



class TestBackendDeviceContext(object):
	PACKET_TYPE_NONE=0x00
	PACKET_TYPE_HOST_INFO=0x90
	PACKET_TYPE_DEVICE_INFO=0x9f
	PACKET_TYPE_ACK=0xb0
	PACKET_TYPE_LED_DRIVER_STATUS_REQUEST=0x7a
	PACKET_TYPE_LED_DRIVER_STATUS_RESPONSE=0x80
	PACKET_TYPE_PROGRAM_CHUNK_REQUEST=0xd5
	PACKET_TYPE_PROGRAM_CHUNK_REQUEST_DEVICE=0x97
	PACKET_TYPE_PROGRAM_CHUNK_RESPONSE=0xf8
	PACKET_TYPE_PROGRAM_SETUP=0xc8
	PACKET_TYPE_PROGRAM_UPLOAD_STATUS=0xa5
	PACKET_TYPE_HARDWARE_DATA_REQUEST=0x2f
	PACKET_TYPE_HARDWARE_DATA_RESPONSE=0x53

	PROTOCOL_VERSION=0x0005

	HANDSHAKE_OPEN=0
	HANDSHAKE_CONNECTED=1

	def __init__(self,path,supported_protocol_version,inject_protocol_error,config):
		self.path=path
		self.supported_protocol_version=supported_protocol_version
		self.inject_protocol_error=inject_protocol_error
		self.config={
			"storage": 4096,
			"hardware": bytearray(8),
			"program_ctrl": 0x000000,
			"program_crc": 0x000000,
			"brightness": 0x00,
			"access_mode": 0x02,
			"psu_current": 0x00,
			"running": False,
			"firmware_version": bytearray(20),
			"serial_number": 0x0000000000000000,
			"driver": {
				"temperature": 0x0000,
				"load": 0x0000,
				"program_offset": 0x00000000,
				"current_usage": 0x00000000
			},
			**config
		}
		self.handshake_state=TestBackendDeviceContext.HANDSHAKE_OPEN
		self.extended_read_data=None

	def _error_packet(self,expected=False):
		if (not expected):
			TestManager.instance().fail("Error packet issued by device",2)
		return struct.pack("<BB",TestBackendDeviceContext.PACKET_TYPE_NONE,2)

	def _process_host_info_packet(self,packet):
		if (len(packet)!=4 or self.handshake_state!=TestBackendDeviceContext.HANDSHAKE_OPEN):
			return self._error_packet()
		protocol_version=struct.unpack("<xxH",packet)[0]
		if (protocol_version!=self.supported_protocol_version):
			return self._error_packet(expected=True)
		if (self.inject_protocol_error):
			return b"\xff"
		self.handshake_state=TestBackendDeviceContext.HANDSHAKE_CONNECTED
		return struct.pack("<BBHH8sIIBBBB20sQ",
			TestBackendDeviceContext.PACKET_TYPE_DEVICE_INFO,
			54,
			self.supported_protocol_version,
			self.config["storage"]>>10,
			self.config["hardware"],
			self.config["program_ctrl"],
			self.config["program_crc"],
			self.config["brightness"]&0x0f,
			self.config["access_mode"]&0x0f,
			self.config["psu_current"]&0x7f,
			int(self.config["running"])&0x01,
			self.config["firmware_version"],
			self.config["serial_number"]
		)

	def _process_led_driver_status_request_packet(self,packet):
		if (len(packet)!=2 or self.handshake_state!=TestBackendDeviceContext.HANDSHAKE_CONNECTED):
			return self._error_packet()
		return struct.pack("<BBHHII8x",
			TestBackendDeviceContext.PACKET_TYPE_LED_DRIVER_STATUS_RESPONSE,
			22,
			self.config["driver"]["temperature"],
			self.config["driver"]["load"],
			self.config["driver"]["program_offset"],
			self.config["driver"]["current_usage"]
		)

	def _process_hardware_data_request_packet(self,packet):
		if (len(packet)!=3 or self.handshake_state!=TestBackendDeviceContext.HANDSHAKE_CONNECTED):
			return self._error_packet()
		self.extended_read_data=bytearray()
		return struct.pack("<BBHH16x",
			TestBackendDeviceContext.PACKET_TYPE_HARDWARE_DATA_RESPONSE,
			22,
			0,
			0
		)

	def process_packet(self,packet):
		if (len(packet)<2 or len(packet)!=packet[1]):
			return self._error_packet()
		if (packet[0]==TestBackendDeviceContext.PACKET_TYPE_HOST_INFO):
			return self._process_host_info_packet(packet)
		if (packet[0]==TestBackendDeviceContext.PACKET_TYPE_LED_DRIVER_STATUS_REQUEST):
			return self._process_led_driver_status_request_packet(packet)
		if (packet[0]==TestBackendDeviceContext.PACKET_TYPE_HARDWARE_DATA_REQUEST):
			return self._process_hardware_data_request_packet(packet)
		return self._error_packet()

	def process_extended_read(self,size):
		if (self.extended_read_data is None or size!=len(self.extended_read_data)):
			TestManager.instance().fail("Invalid extended read")
			return bytearray(size)
		out=bytearray(self.extended_read_data)
		self.extended_read_data=None
		return out



class TestBackend(object):
	def __init__(self,device_list=["/path/to/dev0"],device_supported_protocol_version=TestBackendDeviceContext.PROTOCOL_VERSION,device_inject_protocol_error=False,device_config={}):
		self.device_list=device_list
		self.device_supported_protocol_version=device_supported_protocol_version
		self.device_inject_protocol_error=device_inject_protocol_error
		self.device_config=device_config
		self.context_list=[]
		if (isinstance(LEDSignProtocol._backend,TestBackend)):
			LEDSignProtocol._backend.cleanup()
		LEDSignProtocol._backend=self

	def cleanup(self):
		if (self.context_list):
			TestManager.instance().fail("Not all handles released",3)

	def enumerate(self) -> list[str]:
		return self.device_list

	def open(self,path:str) -> TestBackendDeviceContext:
		if (path not in self.device_list):
			raise FileNotFoundError(path)
		for ctx in self.context_list:
			if (ctx.path==path):
				raise IOError(path)
		out=TestBackendDeviceContext(path,self.device_supported_protocol_version,self.device_inject_protocol_error,self.device_config)
		self.context_list.append(out)
		return out

	def close(self,handle:TestBackendDeviceContext) -> None:
		if (handle not in self.context_list):
			raise ValueError
		self.context_list.remove(handle)

	def io_read_write(self,handle:TestBackendDeviceContext,packet:bytes) -> bytearray:
		if (handle not in self.context_list):
			raise ValueError
		return handle.process_packet(packet)

	def io_bulk_read(self,handle:TestBackendDeviceContext,size:int) -> bytearray:
		if (handle not in self.context_list):
			raise ValueError
		return handle.process_extended_read(size)

	def io_bulk_write(self,handle:TestBackendDeviceContext,data:bytearray) -> None:
		if (handle not in self.context_list):
			raise ValueError
		raise LEDSignProtocolError()



test=TestManager()



@test
def test_device_enumerate():
	TestBackend(device_list=[])
	test.equal(LEDSign.enumerate(),[])
	test.equal(LEDSign.enumerate(),[])
	device_list=["/path/to/dev0","/path/to/dev1"]
	TestBackend(device_list=device_list)
	test.equal(LEDSign.enumerate(),device_list)
	test.equal(LEDSign.enumerate(),device_list)
	TestBackend(device_list=[])
	test.equal(LEDSign.enumerate(),[])
	test.equal(LEDSign.enumerate(),[])



@test
def test_device_open():
	TestBackend(device_list=[])
	test.exception(lambda:LEDSign.open(12345),TypeError)
	test.exception(LEDSign.open,LEDSignDeviceNotFoundError)
	test.exception(lambda:LEDSign.open("/invalid/device/path"),Exception)
	device_list=["/path/to/dev0","/path/to/dev1"]
	TestBackend(device_list=device_list)
	test.equal(LEDSign.open().get_path(),device_list[0])
	test.equal(LEDSign.open(device_list[0]).get_path(),device_list[0])
	test.equal(LEDSign.open(device_list[1]).get_path(),device_list[1])
	TestBackend(device_supported_protocol_version=0xbeef)
	test.exception(LEDSign.open,LEDSignUnsupportedProtocolError)
	TestBackend()
	device=LEDSign.open()
	test.exception(LEDSign.open,Exception)
	device.close()
	TestBackend(device_inject_protocol_error=True)
	test.exception(LEDSign.open,LEDSignProtocolError)



@test
def test_device_close():
	TestBackend()
	device=LEDSign.open()
	program=device.get_program().compile()
	device.close()
	test.exception(device.close,LEDSignAccessError)
	test.exception(device.get_psu_current,LEDSignAccessError)
	test.exception(device.get_storage_size,LEDSignAccessError)
	test.exception(device.get_hardware,LEDSignAccessError)
	test.exception(device.get_firmware,LEDSignAccessError)
	test.exception(device.get_serial_number,LEDSignAccessError)
	test.exception(device.get_serial_number_str,LEDSignAccessError)
	test.exception(device.get_driver_brightness,LEDSignAccessError)
	test.exception(device.is_driver_paused,LEDSignAccessError)
	test.exception(device.get_driver_temperature,LEDSignAccessError)
	test.exception(device.get_driver_load,LEDSignAccessError)
	test.exception(device.get_driver_program_time,LEDSignAccessError)
	test.exception(device.get_driver_current_usage,LEDSignAccessError)
	test.exception(device.get_driver_status_reload_time,LEDSignAccessError)
	test.exception(lambda:device.set_driver_status_reload_time(0.5),LEDSignAccessError)
	test.exception(device.get_program,LEDSignAccessError)
	test.exception(lambda:device.upload_program(program),LEDSignAccessError)



@test
def test_device_access_mode():
	TestBackend(device_config={"access_mode":0x01})
	device=LEDSign.open()
	test.equal(device.get_access_mode(),LEDSign.ACCESS_MODE_READ)
	device.close()
	test.equal(device.get_access_mode(),LEDSign.ACCESS_MODE_NONE)
	TestBackend(device_config={"access_mode":0x02})
	device=LEDSign.open()
	test.equal(device.get_access_mode(),LEDSign.ACCESS_MODE_READ_WRITE)
	device.close()
	test.equal(device.get_access_mode(),LEDSign.ACCESS_MODE_NONE)



@test
def test_device_access_mode_str():
	TestBackend(device_config={"access_mode":0x01})
	device=LEDSign.open()
	test.equal(device.get_access_mode_str(),"read-only")
	device.close()
	test.equal(device.get_access_mode_str(),"none")
	TestBackend(device_config={"access_mode":0x02})
	device=LEDSign.open()
	test.equal(device.get_access_mode_str(),"read-write")
	device.close()
	test.equal(device.get_access_mode_str(),"none")



@test
def test_device_driver_brightness():
	for driver_value,value in [(0,0.00),(1,0.15),(2,0.30),(3,0.45),(4,0.55),(5,0.70),(6,0.85),(7,1.00)]:
		TestBackend(device_config={"brightness":driver_value})
		test.equal(LEDSign.open().get_driver_brightness(),value)



@test
def test_device_driver_current_usage():
	dynamic_driver_config={"temperature":0,"load":0,"program_offset":0,"current_usage":0}
	TestBackend(device_config={"driver":dynamic_driver_config})
	device=LEDSign.open()
	device.set_driver_status_reload_time(-1)
	for _ in range(0,100):
		value=random.randint(0,20_000_000)
		dynamic_driver_config["current_usage"]=value
		test.equal(device.get_driver_current_usage(),value*1e-6)
	device.close()



@test
def test_device_driver_load():
	dynamic_driver_config={"temperature":0,"load":0,"program_offset":0,"current_usage":0}
	TestBackend(device_config={"driver":dynamic_driver_config})
	device=LEDSign.open()
	device.set_driver_status_reload_time(-1)
	for _ in range(0,100):
		value=random.randint(0,65535)
		dynamic_driver_config["load"]=value
		test.equal(device.get_driver_load(),value/160)
	device.close()



@test
def test_device_driver_temperature():
	dynamic_driver_config={"temperature":0,"load":0,"program_offset":0,"current_usage":0}
	TestBackend(device_config={"driver":dynamic_driver_config})
	device=LEDSign.open()
	device.set_driver_status_reload_time(-1)
	for _ in range(0,100):
		value=random.randint(0,65535)
		dynamic_driver_config["temperature"]=value
		test.equal(device.get_driver_temperature(),437.226612-value*0.468137)
	device.close()



@test
def test_device_firmware():
	firmware=bytearray(20)
	firmware_str=""
	for i in range(0,len(firmware)):
		firmware[i]=random.randint(0,255)
		firmware_str+=f"{firmware[i]:02x}"
	TestBackend(device_config={"firmware_version":firmware})
	test.equal(LEDSign.open().get_firmware(),firmware_str)



@test
def test_device_hardware():
	for device_hardware,str_hardware,user_hardware in [
		(b"\x00\x00\x00\x00\x00\x00\x00\x00","[00 00 00 00 00 00 00 00]",""),
		(b"\x00A\x00\x00\x00\x00\x00\x00","[00 41 00 00 00 00 00 00]","A"),
		(b"A\x00B\x00\x00CDE","[41 00 42 00 00 43 44 45]","ABCDE"),
	]:
		TestBackend(device_config={"hardware":device_hardware})
		device=LEDSign.open()
		test.equal(device.get_hardware().get_raw(),device_hardware)
		test.equal(device.get_hardware().get_string(),str_hardware)
		test.equal(device.get_hardware().get_user_string(),user_hardware)
		device.close()



@test
def cleanup_handles():
	TestBackend().cleanup()



test.execute()
