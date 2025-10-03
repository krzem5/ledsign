from ledsign import *
from ledsign.protocol import LEDSignProtocol
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
		if (a==b):
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
		self.handshake_state=TestBackendDeviceContext.HANDSHAKE_OPEN
		self.config={
			**config,
			"storage": 4096,
			"hardware_config": bytearray(8),
			"program_ctrl": 0,
			"program_crc": 0,
			"brightness": 0,
			"access_mode": 1,
			"psu_current": 0,
			"running": False,
			"firmware_version": bytearray(20),
			"serial_number": 0
		}

	def _error_packet(self,expected=False):
		if (not expected):
			TestManager.instance().fail("Error packet issued by device")
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
			self.config["hardware_config"],
			self.config["program_ctrl"],
			self.config["program_crc"],
			self.config["brightness"]&0x0f,
			self.config["access_mode"]&0x0f,
			round(self.config["psu_current"]*10)&0x7f,
			int(self.config["running"])&0x01,
			self.config["firmware_version"],
			self.config["serial_number"]
		)

	def process_packet(self,packet):
		if (len(packet)<2 or len(packet)!=packet[1]):
			return self._error_packet()
		if (packet[0]==TestBackendDeviceContext.PACKET_TYPE_HOST_INFO):
			return self._process_host_info_packet(packet)
		return self._error_packet()



class TestBackend(object):
	def __init__(self,device_list=[],device_supported_protocol_version=TestBackendDeviceContext.PROTOCOL_VERSION,device_inject_protocol_error=False,device_config={}) -> None:
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
		raise LEDSignProtocolError()

	def io_bulk_write(self,handle:TestBackendDeviceContext,data:bytearray) -> None:
		if (handle not in self.context_list):
			raise ValueError
		raise LEDSignProtocolError()



test=TestManager()



@test
def test_device_enumerate():
	TestBackend()
	test.equal(LEDSign.enumerate(),[])
	test.equal(LEDSign.enumerate(),[])
	device_list=["/path/to/dev0","/path/to/dev1"]
	TestBackend(device_list=device_list)
	test.equal(LEDSign.enumerate(),device_list)
	test.equal(LEDSign.enumerate(),device_list)
	TestBackend()
	test.equal(LEDSign.enumerate(),[])
	test.equal(LEDSign.enumerate(),[])



@test
def test_device_open():
	TestBackend()
	test.exception(lambda:LEDSign.open(12345),TypeError)
	test.exception(LEDSign.open,LEDSignDeviceNotFoundError)
	test.exception(lambda:LEDSign.open("/invalid/device/path"),Exception)
	device_list=["/path/to/dev0","/path/to/dev1"]
	TestBackend(device_list=device_list)
	test.equal(LEDSign.open().get_path(),device_list[0])
	test.equal(LEDSign.open(device_list[0]).get_path(),device_list[0])
	test.equal(LEDSign.open(device_list[1]).get_path(),device_list[1])
	TestBackend(device_list=device_list,device_supported_protocol_version=0xbeef)
	test.exception(LEDSign.open,LEDSignUnsupportedProtocolError)
	TestBackend(device_list=device_list)
	device=LEDSign.open()
	test.exception(LEDSign.open,Exception)
	device.close()
	TestBackend(device_list=device_list,device_inject_protocol_error=True)
	test.exception(LEDSign.open,LEDSignProtocolError)



@test
def cleanup_handles():
	TestBackend().cleanup()



test.execute()
