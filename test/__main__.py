from ledsign import *
from ledsign.protocol import LEDSignProtocol
import random
import struct
import sys
import time



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
		try:
			for fn in self._functions:
				fn()
		except Exception as e:
			self.fail("Exception encountered")
			raise e
		finally:
			TestManager._instance=None
			with open("build/test_result.txt","w") as wf:
				wf.write(f"{self._success_count},{self._fail_count}\n")

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

	HARDWARE_SCALE=768

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
			"hardware_data": {},
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
			self.config["storage"],
			(self.config["hardware"]() if callable(self.config["hardware"]) else self.config["hardware"]),
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
		if (len(packet)!=3 or self.handshake_state!=TestBackendDeviceContext.HANDSHAKE_CONNECTED or chr(packet[2]) not in self.config["hardware_data"]):
			return self._error_packet()
		entry=self.config["hardware_data"][chr(packet[2])]
		self.extended_read_data=bytearray()
		for x,y in entry["data"]:
			self.extended_read_data+=struct.pack("<HH",x*TestBackendDeviceContext.HARDWARE_SCALE,y*TestBackendDeviceContext.HARDWARE_SCALE)
		return struct.pack("<BBHH16x",
			TestBackendDeviceContext.PACKET_TYPE_HARDWARE_DATA_RESPONSE,
			22,
			len(self.extended_read_data),
			entry["width"]*TestBackendDeviceContext.HARDWARE_SCALE
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
def test_device_firmware():
	firmware=bytearray(20)
	firmware_str=""
	for i in range(0,len(firmware)):
		firmware[i]=random.randint(0,255)
		firmware_str+=f"{firmware[i]:02x}"
	TestBackend(device_config={"firmware_version":firmware})
	test.equal(LEDSign.open().get_firmware(),firmware_str)



@test
def test_device_path():
	device_list=["/path/to/dev0","/path/to/dev1"]
	TestBackend(device_list=device_list)
	device=LEDSign.open()
	test.equal(device.get_path(),device_list[0])
	device.close()
	test.equal(device.get_path(),None)



@test
def test_device_psu_current():
	for i in range(0,105,5):
		TestBackend(device_config={"psu_current":i})
		test.equal(LEDSign.open().get_psu_current(),i/10)



@test
def test_device_serial_number():
	serial_number=random.getrandbits(64)
	TestBackend(device_config={"serial_number":serial_number})
	test.equal(LEDSign.open().get_serial_number(),serial_number)



@test
def test_device_serial_number_str():
	serial_number=random.getrandbits(64)
	TestBackend(device_config={"serial_number":serial_number})
	test.equal(LEDSign.open().get_serial_number_str(),f"{serial_number:016x}")



@test
def test_device_storage_size():
	for i in range(0,16384,128):
		TestBackend(device_config={"storage":i})
		test.equal(LEDSign.open().get_storage_size(),i<<10)



@test
def test_device_program_upload():
	TestBackend(device_config={"access_mode":0x01})
	device=LEDSign.open()
	test.exception(lambda:device.upload_program("wrong_type"),TypeError)
	test.exception(lambda:device.upload_program(device.get_program().compile()),LEDSignAccessError)
	device.close()



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
def test_device_driver_pause():
	TestBackend(device_config={"running":False})
	test.equal(LEDSign.open().is_driver_paused(),True)
	TestBackend(device_config={"running":True})
	test.equal(LEDSign.open().is_driver_paused(),False)



@test
def test_device_driver_reload_time():
	dynamic_driver_config={"temperature":0,"load":0,"program_offset":0,"current_usage":0}
	TestBackend(device_config={"driver":dynamic_driver_config})
	device=LEDSign.open()
	device.set_driver_status_reload_time(0.5)
	test.equal(device.get_driver_status_reload_time(),0.5)
	test.equal(device.set_driver_status_reload_time(-12345),0.5)
	test.equal(device.get_driver_status_reload_time(),-1)
	device.set_driver_status_reload_time(0.1)
	test.equal(device.get_driver_current_usage(),0.0)
	dynamic_driver_config["current_usage"]=1_000_000
	test.equal(device.get_driver_current_usage(),0.0)
	time.sleep(0.1)
	test.equal(device.get_driver_current_usage(),1.0)
	device.set_driver_status_reload_time(-1)
	test.equal(device.get_driver_current_usage(),1.0)
	dynamic_driver_config["current_usage"]=0
	test.equal(device.get_driver_current_usage(),0.0)
	device.close()



@test
def test_hardware():
	test.exception(lambda:LEDSignHardware(None,None),TypeError)
	TestBackend(device_config={"hardware":lambda:device_hardware,"hardware_data":{chr(i+65):{"data":[],"width":0} for i in range(0,5)}})
	for device_hardware,str_hardware,user_hardware in [
		(b"\x00\x00\x00\x00\x00\x00\x00\x00","[00 00 00 00 00 00 00 00]",""),
		(b"\x00A\x00\x00\x00\x00\x00\x00","[00 41 00 00 00 00 00 00]","A"),
		(b"A\x00B\x00\x00CDE","[41 00 42 00 00 43 44 45]","ABCDE"),
	]:
		device=LEDSign.open()
		test.equal(device.get_hardware().get_raw(),device_hardware)
		test.equal(device.get_hardware().get_string(),str_hardware)
		test.equal(device.get_hardware().get_user_string(),user_hardware)
		device.close()



@test
def test_selector_bounding_box():
	TestBackend(device_config={"hardware":b"A\x00\x00\x00\x00\x00A\x00","hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2}}})
	device=LEDSign.open()
	test.exception(LEDSignSelector.get_bounding_box,TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:LEDSignSelector.get_bounding_box(mask="wrong_type"),TypeError)
		test.exception(lambda:LEDSignSelector.get_bounding_box(hardware="wrong_type"),TypeError)
		test.equal(LEDSignSelector.get_bounding_box(),(0.0,0.0,3.0,1.0))
		test.equal(LEDSignSelector.get_bounding_box(mask=3),(0.0,0.0,1.0,0.0))
		test.equal(LEDSignSelector.get_bounding_box(mask=LEDSignSelector.get_letter_mask(0)),(0.0,0.0,1.0,1.0))
		test.equal(LEDSignSelector.get_bounding_box(mask=LEDSignSelector.get_letter_mask(1)),(2.0,0.0,3.0,1.0))
	device.close()



@test
def test_selector_center():
	TestBackend(device_config={"hardware":b"A\x00\x00\x00\x00\x00A\x00","hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2}}})
	device=LEDSign.open()
	test.exception(LEDSignSelector.get_center,TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:LEDSignSelector.get_center(mask="wrong_type"),TypeError)
		test.exception(lambda:LEDSignSelector.get_center(hardware="wrong_type"),TypeError)
		test.equal(LEDSignSelector.get_center(),(1.5,0.5))
		test.equal(LEDSignSelector.get_center(weighted=True),(5/3,1/3))
		test.equal(LEDSignSelector.get_center(mask=1),(0.0,0.0))
		test.equal(LEDSignSelector.get_center(mask=1,weighted=True),(0.0,0.0))
		test.equal(LEDSignSelector.get_center(mask=LEDSignSelector.get_letter_mask(1)),(2.5,0.5))
		test.equal(LEDSignSelector.get_center(mask=LEDSignSelector.get_letter_mask(1),weighted=True),(8/3,1/3))
	device.close()



@test
def test_selector_circle_mask():
	TestBackend(device_config={"hardware":b"A\x00\x00\x00\x00\x00\x00\x00\x00","hardware_data":{"A":{"data":[(0,0),(1,0),(1,1),(5,5)],"width":6}}})
	device=LEDSign.open()
	test.exception(LEDSignSelector.get_circle_mask,TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:LEDSignSelector.get_circle_mask("wrong_type",0.0,1.0),TypeError)
		test.exception(lambda:LEDSignSelector.get_circle_mask(0.0,"wrong_type",1.0),TypeError)
		test.exception(lambda:LEDSignSelector.get_circle_mask(0.0,0.0,"wrong_type"),TypeError)
		test.exception(lambda:LEDSignSelector.get_circle_mask(0.0,0.0,"wrong_type"),TypeError)
		test.exception(lambda:LEDSignSelector.get_circle_mask(0.0,0.0,-1.0),ValueError)
		test.exception(lambda:LEDSignSelector.get_circle_mask(0.0,0.0,1.0,mask="wrong_type"),TypeError)
		test.exception(lambda:LEDSignSelector.get_circle_mask(hardware="wrong_type"),TypeError)
		test.equal(LEDSignSelector.get_circle_mask(1.0,0.0,0.0),2)
		test.equal(LEDSignSelector.get_circle_mask(1.0,0.5,0.6),6)
		test.equal(LEDSignSelector.get_circle_mask(1.0,0.0,1.0),7)
		test.equal(LEDSignSelector.get_circle_mask(5.0,5.0,4.0),8)
		test.equal(LEDSignSelector.get_circle_mask(5.0,5.0,5.0*2**0.5),15)
		test.equal(LEDSignSelector.get_circle_mask(1.0,0.0,0.0),2)
		test.equal(LEDSignSelector.get_circle_mask(1.0,0.5,0.6,mask=3),2)
	device.close()



@test
def test_selector_mask():
	device_hardware=bytearray(8)
	TestBackend(device_config={"hardware":lambda:device_hardware,"hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2},"B":{"data":[(0,0),(1,0),(1,1),(2,2),(3,3)],"width":4}}})
	device=LEDSign.open()
	test.exception(LEDSignSelector.get_mask,TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:LEDSignSelector.get_mask(hardware="wrong_type"),TypeError)
		test.equal(LEDSignSelector.get_mask(),0)
	device.close()
	device_hardware[0]=65
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_mask(),7))
	device_hardware[5]=65
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_mask(),7|(7<<15)))
	device_hardware[5]=66
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_mask(),7|(31<<25)))



@test
def test_selector_led_depth():
	device_hardware=bytearray(8)
	TestBackend(device_config={"hardware":lambda:device_hardware,"hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2},"B":{"data":[(0,0),(1,0),(1,1),(2,2),(3,3)],"width":4}}})
	device=LEDSign.open()
	test.exception(LEDSignSelector.get_led_depth,TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:LEDSignSelector.get_led_depth(hardware="wrong_type"),TypeError)
		test.equal(LEDSignSelector.get_led_depth(),0)
	device.close()
	device_hardware[0]=65
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_led_depth(),3))
	device_hardware[5]=65
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_led_depth(),3))
	device_hardware[5]=66
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_led_depth(),5))



@test
def test_selector_letter_count():
	device_hardware=bytearray(8)
	TestBackend(device_config={"hardware":lambda:device_hardware,"hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2},"B":{"data":[(0,0),(1,0),(1,1),(2,2),(3,3)],"width":4}}})
	device=LEDSign.open()
	test.exception(LEDSignSelector.get_letter_count,TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:LEDSignSelector.get_letter_count(hardware="wrong_type"),TypeError)
		test.equal(LEDSignSelector.get_letter_count(),0)
	device.close()
	device_hardware[0]=65
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_letter_count(),1))
	device_hardware[5]=65
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_letter_count(),2))
	device_hardware[5]=66
	LEDSignProgram(LEDSign.open())(lambda:test.equal(LEDSignSelector.get_letter_count(),2))



@test
def test_selector_letter_mask():
	TestBackend(device_config={"hardware":b"\x00A\x00\x00BB\x00\x00","hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2},"B":{"data":[(0,0),(1,0),(1,1),(2,2),(3,3)],"width":4}}})
	device=LEDSign.open()
	test.exception(LEDSignSelector.get_letter_mask,TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:LEDSignSelector.get_letter_mask("wrong_type"),TypeError)
		test.exception(lambda:LEDSignSelector.get_letter_mask(-1),IndexError)
		test.exception(lambda:LEDSignSelector.get_letter_mask(3),IndexError)
		test.exception(lambda:LEDSignSelector.get_letter_mask(hardware="wrong_type"),TypeError)
		test.equal(LEDSignSelector.get_letter_mask(0),7<<5)
		test.equal(LEDSignSelector.get_letter_mask(1),31<<20)
		test.equal(LEDSignSelector.get_letter_mask(2),31<<25)
	device.close()



@test
def test_selector_letter_masks():
	TestBackend(device_config={"hardware":b"\x00A\x00\x00BB\x00\x00","hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2},"B":{"data":[(0,0),(1,0),(1,1),(2,2),(3,3)],"width":4}}})
	device=LEDSign.open()
	test.exception(lambda:tuple(LEDSignSelector.get_letter_masks),TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:tuple(LEDSignSelector.get_letter_masks(hardware="wrong_type")),TypeError)
		test.equal(tuple(LEDSignSelector.get_letter_masks()),((0,"A",7<<5),(1,"B",31<<20),(2,"B",31<<25)))
	device.close()



@test
def test_selector_pixels():
	TestBackend(device_config={"hardware":b"A\x00\x00\x00\x00\x00B\x00","hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2},"B":{"data":[(0,0),(1,0),(1,1),(2,2),(3,3)],"width":4}}})
	device=LEDSign.open()
	test.exception(lambda:tuple(LEDSignSelector.get_pixels),TypeError)
	@LEDSignProgram(device)
	def program():
		test.exception(lambda:tuple(LEDSignSelector.get_pixels(mask="wrong_type")),TypeError)
		test.exception(lambda:tuple(LEDSignSelector.get_pixels(letter="wrong_type")),TypeError)
		test.exception(lambda:tuple(LEDSignSelector.get_pixels(letter=-1)),IndexError)
		test.exception(lambda:tuple(LEDSignSelector.get_pixels(letter=2)),IndexError)
		test.exception(lambda:tuple(LEDSignSelector.get_pixels(hardware="wrong_type")),TypeError)
		test.equal(tuple(LEDSignSelector.get_pixels()),((0.0,0.0,1),(1.0,0.0,2),(1.0,1.0,4),(2.0,0.0,1<<30),(3.0,0.0,2<<30),(3.0,1.0,4<<30),(4.0,2.0,8<<30),(5.0,3.0,16<<30)))
		test.equal(tuple(LEDSignSelector.get_pixels(letter=0)),((0.0,0.0,1),(1.0,0.0,2),(1.0,1.0,4)))
		test.equal(tuple(LEDSignSelector.get_pixels(mask=5|LEDSignSelector.get_letter_mask(1),letter=0)),((0.0,0.0,1),(1.0,1.0,4)))
		test.equal(tuple(LEDSignSelector.get_pixels(mask=3|(16<<30))),((0.0,0.0,1),(1.0,0.0,2),(5.0,3.0,16<<30)))
	device.close()



@test
def test_program_load():
	TestBackend(device_config={"hardware":b"A\x00\x00\x00\x00\x00B\x00","hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2},"B":{"data":[(0,0),(1,0),(1,1),(2,2),(3,3)],"width":4}}})
	device=LEDSign.open()
	@LEDSignProgram(device)
	def program():
		kp("#ff0000")
		af(1)
		kp("#00ff00",5)
		af(1)
		kp("#0000ff",duration=0.5)
		af(1)
		end()
	program.save("build/temp.led")
	program=LEDSignProgram(device,"build/temp.led")
	test.equal(program.get_duration(),181/60)
	keypoints=tuple(program.get_keypoints())
	test.equal(len(keypoints),3)
	test.equal(keypoints[0].get_duration(),1/60)
	test.equal(keypoints[0].get_end(),1/60)
	test.equal(keypoints[0].get_mask(),LEDSignSelector.get_mask(hardware=device.get_hardware()))
	test.equal(keypoints[0].get_rgb(),0xff0000)
	test.equal(keypoints[1].get_duration(),1/60)
	test.equal(keypoints[1].get_end(),61/60)
	test.equal(keypoints[1].get_mask(),5)
	test.equal(keypoints[1].get_rgb(),0x00ff00)
	test.equal(keypoints[2].get_duration(),30/60)
	test.equal(keypoints[2].get_end(),121/60)
	test.equal(keypoints[2].get_mask(),LEDSignSelector.get_mask(hardware=device.get_hardware()))
	test.equal(keypoints[2].get_rgb(),0x0000ff)
	device.close()



@test
def test_program_generate():
	print("test_program_generate")



@test
def test_program_compile():
	print("test_program_compile")



@test
def test_program_duration():
	print("test_program_duration")



@test
def test_program_keypoints():
	TestBackend(device_config={"hardware":b"A\x00\x00\x00\x00\x00B\x00","hardware_data":{"A":{"data":[(0,0),(1,0),(1,1)],"width":2},"B":{"data":[(0,0),(1,0),(1,1),(2,2),(3,3)],"width":4}}})
	device=LEDSign.open()
	@LEDSignProgram(device)
	def program():
		kp("#ff0000")
		af(1)
		kp("#2eaa34",5)
		af(1)
		kp("#0000ff",duration=0.5)
		af(1)
		end()
	keypoints=tuple(program.get_keypoints())
	test.equal(len(keypoints),3)
	test.equal(keypoints[0].get_duration(),1/60)
	test.equal(keypoints[0].get_end(),1/60)
	test.equal(keypoints[0].get_mask(),LEDSignSelector.get_mask(hardware=device.get_hardware()))
	test.equal(keypoints[0].get_rgb(),0xff0000)
	test.equal(keypoints[0].get_rgb_html(),"#ff0000")
	test.equal(keypoints[0].get_start(),0/60)
	test.equal(keypoints[1].get_duration(),1/60)
	test.equal(keypoints[1].get_end(),61/60)
	test.equal(keypoints[1].get_mask(),5)
	test.equal(keypoints[1].get_rgb(),0x2eaa34)
	test.equal(keypoints[1].get_rgb_html(),"#2eaa34")
	test.equal(keypoints[1].get_start(),60/60)
	test.equal(keypoints[2].get_duration(),30/60)
	test.equal(keypoints[2].get_end(),121/60)
	test.equal(keypoints[2].get_mask(),LEDSignSelector.get_mask(hardware=device.get_hardware()))
	test.equal(keypoints[2].get_rgb(),0x0000ff)
	test.equal(keypoints[2].get_rgb_html(),"#0000ff")
	test.equal(keypoints[2].get_start(),91/60)
	device.close()



@test
def test_program_load():
	print("test_program_load")



@test
def test_program_save():
	print("test_program_save")



@test
def test_program_verify():
	print("test_program_verify")



@test
def cleanup_handles():
	TestBackend().cleanup()



test.execute()
