from ledsign import *
from ledsign.protocol import LEDSignProtocol
import struct



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
		return self.fail()

	def exception(self,fn,exception):
		try:
			fn()
			return self.fail()
		except Exception as e:
			if (not isinstance(e,exception)):
				return self.fail()
		self._success_count+=1
		return True

	def fail(self):
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

	def __init__(self,path,supported_protocol_version):
		self.path=path
		self.supported_protocol_version=supported_protocol_version
		self.handshake_state=TestBackendDeviceContext.HANDSHAKE_OPEN

	def _error_packet(self,expected=False):
		if (not expected):
			TestManager.instance().fail()
		return struct.pack("<BB",TestBackendDeviceContext.PACKET_TYPE_NONE,2)

	def _process_host_info_packet(self,packet):
		if (len(packet)!=4 or self.handshake_state!=TestBackendDeviceContext.HANDSHAKE_OPEN):
			return self._error_packet()
		protocol_version=struct.unpack("<xxH",packet)[0]
		if (protocol_version!=self.supported_protocol_version):
			return self._error_packet(expected=True)
		self.handshake_state=TestBackendDeviceContext.HANDSHAKE_CONNECTED
		return self._error_packet()

	def process_packet(self,packet):
		if (len(packet)<2 or len(packet)!=packet[1]):
			return self._error_packet()
		if (packet[0]==TestBackendDeviceContext.PACKET_TYPE_HOST_INFO):
			return self._process_host_info_packet(packet)
		return self._error_packet()



class TestBackend(object):
	def __init__(self,device_list=[],supported_protocol_version=TestBackendDeviceContext.PROTOCOL_VERSION) -> None:
		self.device_list=device_list
		self.supported_protocol_version=supported_protocol_version
		self.context_list=[]
		LEDSignProtocol._backend=self

	def __del__(self):
		if (self.context_list):
			TestManager.instance().fail()

	def enumerate(self) -> list[str]:
		return self.device_list

	def open(self,path:str) -> TestBackendDeviceContext:
		if (path not in self.device_list):
			raise FileNotFoundError(path)
		for ctx in self.context_list:
			if (ctx.path==path):
				raise IOError(path)
		out=TestBackendDeviceContext(path,self.supported_protocol_version)
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



test.execute()
