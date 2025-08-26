from ledsign.backend import LEDSignProtocolBackendWindows,LEDSignProtocolBackendLinux
import struct
import sys



__all__=["LEDSignProtocolError","LEDSignUnsupportedProtocolError","LEDSignProtocol"]



LEDSignProtocolError=type("LEDSignProtocolError",(Exception,),{})
LEDSignUnsupportedProtocolError=type("LEDSignUnsupportedProtocolError",(Exception,),{})



class LEDSignProtocol(object):
	PACKET_TYPE_NONE=0x00
	PACKET_TYPE_HOST_INFO=0x90
	PACKET_TYPE_DEVICE_INFO=0x9f
	PACKET_TYPE_ACK=0xb0
	PACKET_TYPE_LED_DRIVER_STATUS_REQUEST=0x7a
	PACKET_TYPE_LED_DRIVER_STATUS_RESPONSE=0x80
	PACKET_TYPE_PROGRAM_CHUNK_REQUEST=0xd5
	PACKET_TYPE_PROGRAM_CHUNK_RESPONSE=0xf8
	PACKET_TYPE_PROGRAM_SETUP=0xc8
	PACKET_TYPE_PROGRAM_UPLOAD_STATUS=0xa5
	PACKET_TYPE_HARDWARE_DATA_REQUEST=0x2f
	PACKET_TYPE_HARDWARE_DATA_RESPONSE=0x53

	VERSION=0x0005

	PACKET_FORMATS={
		PACKET_TYPE_NONE: "<BB",
		PACKET_TYPE_HOST_INFO: "<BBH",
		PACKET_TYPE_DEVICE_INFO: "<BBHH8sIIBBBB7sQ",
		PACKET_TYPE_ACK: "<BBB",
		PACKET_TYPE_LED_DRIVER_STATUS_REQUEST: "<BB",
		PACKET_TYPE_LED_DRIVER_STATUS_RESPONSE: "<BBHHII",
		PACKET_TYPE_PROGRAM_CHUNK_REQUEST: "<BBII",
		PACKET_TYPE_PROGRAM_CHUNK_RESPONSE: "<BBI",
		PACKET_TYPE_PROGRAM_SETUP: "<BBII",
		PACKET_TYPE_PROGRAM_UPLOAD_STATUS: "<BB",
		PACKET_TYPE_HARDWARE_DATA_REQUEST: "<BBB",
		PACKET_TYPE_HARDWARE_DATA_RESPONSE: "<BBHH16s"
	}

	_backend=None

	@staticmethod
	def _init():
		if (LEDSignProtocol._backend is None):
			LEDSignProtocol._backend=(LEDSignProtocolBackendWindows if sys.platform=="win32" else LEDSignProtocolBackendLinux)()

	@staticmethod
	def enumerate():
		LEDSignProtocol._init()
		return LEDSignProtocol._backend.enumerate()

	@staticmethod
	def open(path):
		LEDSignProtocol._init()
		return LEDSignProtocol._backend.open(path)

	@staticmethod
	def close(handle):
		LEDSignProtocol._init()
		return LEDSignProtocol._backend.close(handle)

	@staticmethod
	def process_packet(handle,ret_type,type,*args):
		LEDSignProtocol._init()
		ret=LEDSignProtocol._backend.io_read_write(handle,struct.pack(LEDSignProtocol.PACKET_FORMATS[type],type,struct.calcsize(LEDSignProtocol.PACKET_FORMATS[type]),*args))
		if (len(ret)<2 or ret[0]!=ret_type or ret[1]!=len(ret) or ret[1]!=struct.calcsize(LEDSignProtocol.PACKET_FORMATS[ret_type])):
			if (ret_type==LEDSignProtocol.PACKET_TYPE_DEVICE_INFO and type==LEDSignProtocol.PACKET_TYPE_HOST_INFO):
				raise LEDSignUnsupportedProtocolError("Protocol version not supported")
			raise LEDSignProtocolError("Protocol error")
		return struct.unpack(LEDSignProtocol.PACKET_FORMATS[ret_type],ret)[2:]

	@staticmethod
	def process_extended_read(handle,size):
		LEDSignProtocol._init()
		return LEDSignProtocol._backend.io_bulk_read(handle,size)

	@staticmethod
	def process_extended_write(handle,data):
		LEDSignProtocol._init()
		return LEDSignProtocol._backend.io_bulk_write(handle,data)
