import array
import ctypes
import os
import struct
import sys
import threading
import time
import weakref



__all__=["LEDSign","LEDSignProgram","LEDSignProgramBuilder","LEDSignSelector","LEDSignDeviceNotFoundError","LEDSignDeviceInUseError","LEDSignProtocolError","LEDSignUnsupportedProtocolError","LEDSignProgramError","LEDSignAccessError"]



LEDSignDeviceNotFoundError=type("LEDSignDeviceNotFoundError",(Exception,),{})
LEDSignDeviceInUseError=type("LEDSignDeviceInUseError",(Exception,),{})
LEDSignProtocolError=type("LEDSignProtocolError",(Exception,),{})
LEDSignUnsupportedProtocolError=type("LEDSignUnsupportedProtocolError",(Exception,),{})
LEDSignProgramError=type("LEDSignProgramError",(Exception,),{})
LEDSignAccessError=type("LEDSignAccessError",(Exception,),{})



def _bit_permute_step(a,b,c):
	t=((a>>c)^a)&b
	return (a^t)^(t<<c)



class LEDSignProtocolBackendWindows(object):
	CM_GET_DEVICE_INTERFACE_LIST_ALL_DEVICES=0x00000000
	CR_BUFFER_SMALL=0x0000001a
	GENERIC_WRITE=0x40000000
	GENERIC_READ=0x80000000
	FILE_SHARE_READ=0x00000001
	FILE_SHARE_WRITE=0x00000002
	OPEN_EXISTING=0x00000003
	FILE_ATTRIBUTE_NORMAL=0x00000080
	FILE_FLAG_OVERLAPPED=0x40000000

	def __init__(self):
		import ctypes.wintypes
		GUID=type("GUID",(ctypes.Structure,),{"_fields_":[("Data1",ctypes.wintypes.DWORD),("Data2",ctypes.wintypes.WORD),("Data3",ctypes.wintypes.WORD),("Data4",ctypes.wintypes.BYTE*8)]})
		PGUID=ctypes.POINTER(GUID)
		self.CM_Get_Device_Interface_List_SizeA=ctypes.windll.cfgmgr32.CM_Get_Device_Interface_List_SizeA
		self.CM_Get_Device_Interface_List_SizeA.argtypes=(ctypes.wintypes.PULONG,PGUID,ctypes.wintypes.LPVOID,ctypes.wintypes.ULONG)
		self.CM_Get_Device_Interface_List_SizeA.restype=ctypes.wintypes.DWORD
		self.CM_Get_Device_Interface_ListA=ctypes.windll.cfgmgr32.CM_Get_Device_Interface_ListA
		self.CM_Get_Device_Interface_ListA.argtypes=(PGUID,ctypes.wintypes.LPVOID,ctypes.wintypes.PCHAR,ctypes.wintypes.ULONG,ctypes.wintypes.ULONG)
		self.CM_Get_Device_Interface_ListA.restype=ctypes.wintypes.DWORD
		self.CreateFileA=ctypes.windll.kernel32.CreateFileA
		self.CreateFileA.argtypes=(ctypes.wintypes.LPCSTR,ctypes.wintypes.DWORD,ctypes.wintypes.DWORD,ctypes.wintypes.LPVOID,ctypes.wintypes.DWORD,ctypes.wintypes.DWORD,ctypes.wintypes.HANDLE)
		self.CreateFileA.restype=ctypes.wintypes.HANDLE
		self.CloseHandle=ctypes.windll.kernel32.CloseHandle
		self.CloseHandle.argtypes=(ctypes.wintypes.HANDLE,)
		self.CloseHandle.restype=ctypes.wintypes.BOOL
		self.WinUsb_Initialize=ctypes.windll.winusb.WinUsb_Initialize
		self.WinUsb_Initialize.argtypes=(ctypes.wintypes.HANDLE,ctypes.POINTER(ctypes.wintypes.HANDLE))
		self.WinUsb_Initialize.restype=ctypes.wintypes.BOOL
		self.WinUsb_Free=ctypes.windll.winusb.WinUsb_Free
		self.WinUsb_Free.argtypes=(ctypes.wintypes.HANDLE,)
		self.WinUsb_Free.restype=ctypes.wintypes.BOOL
		self.WinUsb_ControlTransfer=ctypes.windll.winusb.WinUsb_ControlTransfer
		self.WinUsb_ControlTransfer.argtypes=(ctypes.wintypes.HANDLE,ctypes.c_ulonglong,ctypes.wintypes.PCHAR,ctypes.wintypes.ULONG,ctypes.wintypes.PULONG,ctypes.wintypes.LPVOID)
		self.WinUsb_ControlTransfer.restype=ctypes.wintypes.BOOL
		self.WinUsb_ReadPipe=ctypes.windll.winusb.WinUsb_ReadPipe
		self.WinUsb_ReadPipe.argtypes=(ctypes.wintypes.HANDLE,ctypes.wintypes.CHAR,ctypes.wintypes.PCHAR,ctypes.wintypes.ULONG,ctypes.wintypes.PULONG,ctypes.wintypes.LPVOID)
		self.WinUsb_ReadPipe.restype=ctypes.wintypes.BOOL
		self.WinUsb_WritePipe=ctypes.windll.winusb.WinUsb_WritePipe
		self.WinUsb_WritePipe.argtypes=(ctypes.wintypes.HANDLE,ctypes.wintypes.CHAR,ctypes.wintypes.PCHAR,ctypes.wintypes.ULONG,ctypes.wintypes.PULONG,ctypes.wintypes.LPVOID)
		self.WinUsb_WritePipe.restype=ctypes.wintypes.BOOL
		self.winusb_registry_guid_ref=ctypes.byref(GUID.from_buffer(bytearray(b"\x58\x30\xf5\xfc\x7b\x99\x21\x4b\xaf\xd6\xe5\x65\x04\x39\x23\xc1")))

	def enumerate(self):
		while (True):
			length=ctypes.wintypes.ULONG(0)
			if (self.CM_Get_Device_Interface_List_SizeA(ctypes.byref(length),self.winusb_registry_guid_ref,0,LEDSignProtocolBackendWindows.CM_GET_DEVICE_INTERFACE_LIST_ALL_DEVICES)):
				raise OSError("CM_Get_Device_Interface_List_SizeA error")
			data=(ctypes.wintypes.CHAR*length.value)()
			ret=self.CM_Get_Device_Interface_ListA(self.winusb_registry_guid_ref,0,data,length,LEDSignProtocolBackendWindows.CM_GET_DEVICE_INTERFACE_LIST_ALL_DEVICES)
			if (not ret):
				return [e for e in bytes(data).decode("utf-8").split("\x00") if e]
			if (ret==LEDSignProtocolBackendWindows.CR_BUFFER_SMALL):
				continue
			raise OSError("CM_Get_Device_Interface_ListA error")

	def open(self,path):
		handle=self.CreateFileA(path.encode("utf-8"),LEDSignProtocolBackendWindows.GENERIC_WRITE|LEDSignProtocolBackendWindows.GENERIC_READ,LEDSignProtocolBackendWindows.FILE_SHARE_READ|LEDSignProtocolBackendWindows.FILE_SHARE_WRITE,0,LEDSignProtocolBackendWindows.OPEN_EXISTING,LEDSignProtocolBackendWindows.FILE_ATTRIBUTE_NORMAL|LEDSignProtocolBackendWindows.FILE_FLAG_OVERLAPPED,0)
		if (handle==0xffffffffffffffff):
			raise LEDSignDeviceInUseError("Device already in use")
		winusb_handle=ctypes.wintypes.HANDLE(0)
		if (not self.WinUsb_Initialize(handle,ctypes.byref(winusb_handle))):
			self.CloseHandle(handle)
			raise LEDSignDeviceInUseError("Device already in use")
		buffer=(ctypes.wintypes.CHAR*64)()
		transferred=ctypes.c_ulong(0)
		if (not self.WinUsb_ControlTransfer(winusb_handle.value,0x00400000545352c0,buffer,64,ctypes.byref(transferred),0) or transferred.value!=5 or bytes(buffer[:5])!=b"reset"):
			self.WinUsb_Free(winusb_handle.value)
			self.CloseHandle(handle)
			raise LEDSignProtocolError("Unable to reset device")
		return (handle,winusb_handle.value)

	def close(self,handles):
		self.WinUsb_Free(handles[1])
		self.CloseHandle(handles[0])

	def io_read_write(self,handles,packet):
		packet=bytearray(packet)
		transferred=ctypes.c_ulong(0)
		if (not self.WinUsb_WritePipe(handles[1],0x04,(ctypes.c_char*len(packet)).from_buffer(packet),len(packet),ctypes.byref(transferred),0) or transferred.value!=len(packet)):
			raise LEDSignProtocolError("Write to endpoint 04h failed")
		transferred.value=0
		out=(ctypes.c_char*64)()
		if (not self.WinUsb_ReadPipe(handles[1],0x84,out,64,ctypes.byref(transferred),0) or transferred.value<2 or transferred.value>64):
			raise LEDSignProtocolError("Read from endpoint 84h failed")
		return bytearray(out)[:transferred.value]

	def io_bulk_read(self,handles,size):
		out=(ctypes.c_char*size)()
		transferred=ctypes.c_ulong(0)
		if (not self.WinUsb_ReadPipe(handles[1],0x85,out,size,ctypes.byref(transferred),0) or transferred.value!=size):
			raise LEDSignProtocolError("Read from endpoint 85h failed")
		return bytearray(out)

	def io_bulk_write(self,handles,data):
		data=bytearray(data)
		transferred=ctypes.c_ulong(0)
		if (not self.WinUsb_WritePipe(handles[1],0x05,(ctypes.c_char*len(data)).from_buffer(data),len(data),ctypes.byref(transferred),0) or transferred.value!=len(data)):
			raise LEDSignProtocolError("Write to endpoint 05h failed")



class LEDSignProtocolBackendLinux(object):
	USBDEVFS_BULK=0xc0185502
	USBDEVFS_CLAIMINTERFACE=0x8004550f
	USBDEVFS_CONTROL=0xc0185500

	def __init__(self):
		import ctypes.util
		self.ioctl=ctypes.CDLL(ctypes.util.find_library("c"),use_errno=True).ioctl
		self.ioctl.argtypes=(ctypes.c_int,ctypes.c_ulong,ctypes.c_char_p)
		self.ioctl.restype=ctypes.c_int

	def enumerate(self):
		out=[]
		for name in os.listdir("/sys/bus/usb/devices"):
			if (not os.path.exists(f"/sys/bus/usb/devices/{name}/idVendor")):
				continue
			with open(f"/sys/bus/usb/devices/{name}/idVendor","rb") as rf:
				if (rf.read()!=b"fff0\n"):
					continue
			with open(f"/sys/bus/usb/devices/{name}/idProduct","rb") as rf:
				if (rf.read()!=b"1000\n"):
					continue
			with open(f"/sys/bus/usb/devices/{name}/busnum","rb") as rf:
				busnum=int(rf.read())
			with open(f"/sys/bus/usb/devices/{name}/devnum","rb") as rf:
				devnum=int(rf.read())
			out.append(f"/dev/bus/usb/{busnum:03d}/{devnum:03d}")
		return out

	def open(self,path):
		handle=os.open(path,os.O_RDWR)
		if (self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_CLAIMINTERFACE,struct.pack("<I",1))<0):
			raise LEDSignDeviceInUseError("Device already in use")
		buffer=(ctypes.c_uint8*64)()
		if (self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_CONTROL,struct.pack("<BBHHHI4xQ",0xc0,0x52,0x5453,0,64,1000,ctypes.addressof(buffer)))!=5 or bytes(buffer[:5])!=b"reset"):
			os.close(handle)
			raise LEDSignProtocolError("Unable to reset device, Python API disabled")
		return handle

	def close(self,handles):
		os.close(handles)

	def io_read_write(self,handle,packet):
		packet=bytearray(packet)
		if (self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_BULK,struct.pack("<III4xQ",0x04,len(packet),1000,ctypes.addressof((ctypes.c_uint8*len(packet)).from_buffer(packet))))!=len(packet)):
			raise LEDSignProtocolError("Write to endpoint 04h failed")
		out=(ctypes.c_uint8*64)()
		ret=self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_BULK,struct.pack("<III4xQ",0x84,64,1000,ctypes.addressof(out)))
		if (ret<2 or ret>64):
			raise LEDSignProtocolError("Read from endpoint 84h failed")
		return bytearray(out)[:ret]

	def io_bulk_read(self,handle,size):
		out=(ctypes.c_uint8*size)()
		ret=self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_BULK,struct.pack("<III4xQ",0x85,size,1000,ctypes.addressof(out)))
		if (ret!=size):
			raise LEDSignProtocolError("Read from endpoint 85h failed")
		return bytearray(out)

	def io_bulk_write(self,handle,data):
		data=bytearray(data)
		if (self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_BULK,struct.pack("<III4xQ",0x05,len(data),1000,ctypes.addressof((ctypes.c_uint8*len(data)).from_buffer(data))))!=len(data)):
			raise LEDSignProtocolError("Write to endpoint 05h failed")



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



class LEDSignCRC(object):
	TABLE=[
		0x00000000,0x04c11db7,0x09823b6e,0x0d4326d9,0x130476dc,0x17c56b6b,0x1a864db2,0x1e475005,
		0x2608edb8,0x22c9f00f,0x2f8ad6d6,0x2b4bcb61,0x350c9b64,0x31cd86d3,0x3c8ea00a,0x384fbdbd,
		0x4c11db70,0x48d0c6c7,0x4593e01e,0x4152fda9,0x5f15adac,0x5bd4b01b,0x569796c2,0x52568b75,
		0x6a1936c8,0x6ed82b7f,0x639b0da6,0x675a1011,0x791d4014,0x7ddc5da3,0x709f7b7a,0x745e66cd,
		0x9823b6e0,0x9ce2ab57,0x91a18d8e,0x95609039,0x8b27c03c,0x8fe6dd8b,0x82a5fb52,0x8664e6e5,
		0xbe2b5b58,0xbaea46ef,0xb7a96036,0xb3687d81,0xad2f2d84,0xa9ee3033,0xa4ad16ea,0xa06c0b5d,
		0xd4326d90,0xd0f37027,0xddb056fe,0xd9714b49,0xc7361b4c,0xc3f706fb,0xceb42022,0xca753d95,
		0xf23a8028,0xf6fb9d9f,0xfbb8bb46,0xff79a6f1,0xe13ef6f4,0xe5ffeb43,0xe8bccd9a,0xec7dd02d,
		0x34867077,0x30476dc0,0x3d044b19,0x39c556ae,0x278206ab,0x23431b1c,0x2e003dc5,0x2ac12072,
		0x128e9dcf,0x164f8078,0x1b0ca6a1,0x1fcdbb16,0x018aeb13,0x054bf6a4,0x0808d07d,0x0cc9cdca,
		0x7897ab07,0x7c56b6b0,0x71159069,0x75d48dde,0x6b93dddb,0x6f52c06c,0x6211e6b5,0x66d0fb02,
		0x5e9f46bf,0x5a5e5b08,0x571d7dd1,0x53dc6066,0x4d9b3063,0x495a2dd4,0x44190b0d,0x40d816ba,
		0xaca5c697,0xa864db20,0xa527fdf9,0xa1e6e04e,0xbfa1b04b,0xbb60adfc,0xb6238b25,0xb2e29692,
		0x8aad2b2f,0x8e6c3698,0x832f1041,0x87ee0df6,0x99a95df3,0x9d684044,0x902b669d,0x94ea7b2a,
		0xe0b41de7,0xe4750050,0xe9362689,0xedf73b3e,0xf3b06b3b,0xf771768c,0xfa325055,0xfef34de2,
		0xc6bcf05f,0xc27dede8,0xcf3ecb31,0xcbffd686,0xd5b88683,0xd1799b34,0xdc3abded,0xd8fba05a,
		0x690ce0ee,0x6dcdfd59,0x608edb80,0x644fc637,0x7a089632,0x7ec98b85,0x738aad5c,0x774bb0eb,
		0x4f040d56,0x4bc510e1,0x46863638,0x42472b8f,0x5c007b8a,0x58c1663d,0x558240e4,0x51435d53,
		0x251d3b9e,0x21dc2629,0x2c9f00f0,0x285e1d47,0x36194d42,0x32d850f5,0x3f9b762c,0x3b5a6b9b,
		0x0315d626,0x07d4cb91,0x0a97ed48,0x0e56f0ff,0x1011a0fa,0x14d0bd4d,0x19939b94,0x1d528623,
		0xf12f560e,0xf5ee4bb9,0xf8ad6d60,0xfc6c70d7,0xe22b20d2,0xe6ea3d65,0xeba91bbc,0xef68060b,
		0xd727bbb6,0xd3e6a601,0xdea580d8,0xda649d6f,0xc423cd6a,0xc0e2d0dd,0xcda1f604,0xc960ebb3,
		0xbd3e8d7e,0xb9ff90c9,0xb4bcb610,0xb07daba7,0xae3afba2,0xaafbe615,0xa7b8c0cc,0xa379dd7b,
		0x9b3660c6,0x9ff77d71,0x92b45ba8,0x9675461f,0x8832161a,0x8cf30bad,0x81b02d74,0x857130c3,
		0x5d8a9099,0x594b8d2e,0x5408abf7,0x50c9b640,0x4e8ee645,0x4a4ffbf2,0x470cdd2b,0x43cdc09c,
		0x7b827d21,0x7f436096,0x7200464f,0x76c15bf8,0x68860bfd,0x6c47164a,0x61043093,0x65c52d24,
		0x119b4be9,0x155a565e,0x18197087,0x1cd86d30,0x029f3d35,0x065e2082,0x0b1d065b,0x0fdc1bec,
		0x3793a651,0x3352bbe6,0x3e119d3f,0x3ad08088,0x2497d08d,0x2056cd3a,0x2d15ebe3,0x29d4f654,
		0xc5a92679,0xc1683bce,0xcc2b1d17,0xc8ea00a0,0xd6ad50a5,0xd26c4d12,0xdf2f6bcb,0xdbee767c,
		0xe3a1cbc1,0xe760d676,0xea23f0af,0xeee2ed18,0xf0a5bd1d,0xf464a0aa,0xf9278673,0xfde69bc4,
		0x89b8fd09,0x8d79e0be,0x803ac667,0x84fbdbd0,0x9abc8bd5,0x9e7d9662,0x933eb0bb,0x97ffad0c,
		0xafb010b1,0xab710d06,0xa6322bdf,0xa2f33668,0xbcb4666d,0xb8757bda,0xb5365d03,0xb1f740b4
	]

	def __init__(self,data=None):
		self.value=0
		if (data is not None):
			self.update(data)

	def update(self,data):
		for e in data:
			self.value=LEDSignCRC.TABLE[(self.value>>24)^e]^((self.value&0xffffff)<<8)



class LEDSignHardware(object):
	SCALE=1/768

	__slots__=["_raw_config","_led_depth","_pixels","_pixel_count","_max_x","_max_y","_mask"]

	def __init__(self,handle,config):
		if (not isinstance(config,bytes) or len(config)!=8):
			raise RuntimeError
		self._raw_config=config
		self._led_depth=0
		self._pixels=[]
		self._pixel_count=0
		self._max_x=0
		self._max_y=0
		self._mask=0
		width_map={0:0}
		geometry_map={0:array.array("H")}
		for i in range(0,8):
			key=self._raw_config[i]
			if (key not in geometry_map):
				geometry_map[key]=array.array("I")
				length,width,_=LEDSignProtocol.process_packet(handle,LEDSignProtocol.PACKET_TYPE_HARDWARE_DATA_RESPONSE,LEDSignProtocol.PACKET_TYPE_HARDWARE_DATA_REQUEST,key)
				width_map[key]=width*LEDSignHardware.SCALE
				geometry_map[key].frombytes(LEDSignProtocol.process_extended_read(handle,length))
			self._led_depth=max(self._led_depth,len(geometry_map[key]))
		for i in range(0,8):
			geometry=geometry_map.get(self._raw_config[i],[])
			self._pixel_count+=len(geometry)
			for xy in geometry:
				x=(xy&0xffff)*LEDSignHardware.SCALE
				y=(xy>>16)*LEDSignHardware.SCALE
				self._max_y=max(self._max_y,y)
				self._mask|=1<<len(self._pixels)
				self._pixels.append((self._max_x+x,y))
			self._max_x+=width_map[self._raw_config[i]]
			for j in range(len(geometry),self._led_depth):
				self._pixels.append(None)
		self._max_x=max(self._max_x,0)

	def __repr__(self):
		return f"<LEDSignHardware config={self.get_string()} pixels={self._pixel_count} led_depth={self._led_depth}>"

	def get_string(self):
		return "["+" ".join([f"{e:02x}" for e in self._raw_config])+"]"



class LEDSignProgramParser(object):
	MAX_LINE_EXTRACTION_ERROR=2

	__slots__=["_program","_frame_length","_offset","_stride","_pixel_prev_states","_pixel_curr_states","_pixel_update_stack","_pixel_update_stack_length","_pixel_masks"]

	def __init__(self,program,frame_length,is_compressed):
		self._program=program
		self._frame_length=frame_length
		self._offset=0
		self._stride=frame_length*12
		self._pixel_prev_states=[0 for _ in range(0,frame_length<<3)]
		self._pixel_curr_states=[0 for _ in range(0,frame_length<<3)]
		self._pixel_update_stack=[0 for _ in range(0,frame_length<<3)]
		self._pixel_update_stack_length=0
		self._pixel_masks=[]
		if (is_compressed):
			for i,pixel in enumerate(program._hardware._pixels):
				if (pixel is None):
					continue
				self._pixel_masks.append(1<<i)
			while (len(self._pixel_masks)<(frame_length<<3)):
				self._pixel_masks.append(0)
		else:
			for i in range(0,frame_length<<3):
				self._pixel_masks.append(1<<i)

	def update(self,data):
		for i in range(0,len(data),12):
			rvec,gvec,bvec=struct.unpack("<III",data[i:i+12])
			rvec=_bit_permute_step(rvec,0x0a0a0a0a,3)
			gvec=_bit_permute_step(gvec,0x0a0a0a0a,3)
			bvec=_bit_permute_step(bvec,0x0a0a0a0a,3)
			rvec=_bit_permute_step(rvec,0x00cc00cc,6)
			gvec=_bit_permute_step(gvec,0x00cc00cc,6)
			bvec=_bit_permute_step(bvec,0x00cc00cc,6)
			rvec=_bit_permute_step(rvec,0x0000f0f0,12)
			gvec=_bit_permute_step(gvec,0x0000f0f0,12)
			bvec=_bit_permute_step(bvec,0x0000f0f0,12)
			rvec=_bit_permute_step(rvec,0x0000ff00,8)
			gvec=_bit_permute_step(gvec,0x0000ff00,8)
			bvec=_bit_permute_step(bvec,0x0000ff00,8)
			j=(self._offset+i)%(self._stride<<1)
			j=j//12+3*self._frame_length*(j>=self._stride)
			for k in range(0,4):
				prev=self._pixel_prev_states[j]
				curr=self._pixel_curr_states[j]
				d=(curr>>24)&0xfffff
				err_r=(rvec&0xff)*d-((curr>>16)&0xff)*(d+1)+((prev>>16)&0xff)
				err_g=(gvec&0xff)*d-((curr>>8)&0xff)*(d+1)+((prev>>8)&0xff)
				err_b=(bvec&0xff)*d-(curr&0xff)*(d+1)+(prev&0xff)
				if (not prev or abs(err_r)+abs(err_g)+abs(err_b)>d*LEDSignProgramParser.MAX_LINE_EXTRACTION_ERROR):
					self._pixel_prev_states[j]=curr;
					if (curr and (not prev or ((curr^prev)&0xffffff))):
						self._pixel_update_stack[self._pixel_update_stack_length]=j
						self._pixel_update_stack_length+=1
					curr&=0xfffff00000000000
				self._pixel_curr_states[j]=(curr&0xffffffffff000000)+((rvec&0xff)<<16)+((gvec&0xff)<<8)+(bvec&0xff)+0x0000100001000000
				rvec>>=8
				gvec>>=8
				bvec>>=8
				j+=self._frame_length
			if ((self._offset+i+12)%(self._stride<<1)):
				continue
			while (self._pixel_update_stack_length):
				value=self._pixel_prev_states[self._pixel_update_stack[0]]
				mask=0
				j=0
				while (j<self._pixel_update_stack_length):
					if (self._pixel_prev_states[self._pixel_update_stack[j]]==value):
						mask|=self._pixel_masks[self._pixel_update_stack[j]]
						self._pixel_update_stack_length-=1
						self._pixel_update_stack[j]=self._pixel_update_stack[self._pixel_update_stack_length]
					else:
						j+=1
				self._program._add_raw_keypoint(value&0xffffff,value>>44,(value>>24)&0xfffff,mask,None)
		self._offset+=len(data)

	def terminate(self):
		for i in range(0,self._frame_length<<3):
			if ((self._pixel_prev_states[i]^self._pixel_curr_states[i])&0xffffff):
				self._pixel_update_stack[self._pixel_update_stack_length]=i
				self._pixel_update_stack_length+=1
		while (self._pixel_update_stack_length):
			value=self._pixel_curr_states[self._pixel_update_stack[0]]
			mask=0
			i=0
			while (i<self._pixel_update_stack_length):
				if (self._pixel_curr_states[self._pixel_update_stack[i]]==value):
					mask|=self._pixel_masks[self._pixel_update_stack[i]]
					self._pixel_update_stack_length-=1
					self._pixel_update_stack[i]=self._pixel_update_stack[self._pixel_update_stack_length]
				else:
					i+=1
			self._program._add_raw_keypoint(value&0xffffff,value>>44,(value>>24)&0xfffff,mask,None)



class LEDSignCompilationPixel(object):
	__slots__=["r","g","b","prev_r","prev_g","prev_b","mask","kp"]

	def __init__(self,mask,kp):
		self.r=0
		self.g=0
		self.b=0
		self.prev_r=0
		self.prev_g=0
		self.prev_b=0
		self.mask=mask
		self.kp=kp



class LEDSignCompiledProgram(object):
	__slots__=["_data","_led_depth","_max_offset","_offset_divisor","_ctrl","_crc"]

	def __init__(self,program,is_compressed):
		pixel_states=[]
		if (is_compressed):
			self._led_depth=(program._hardware._pixel_count+7)>>3
			for i,pixel in enumerate(program._hardware._pixels):
				if (pixel is None):
					continue
				pixel_states.append(LEDSignCompilationPixel(1<<i,program._keypoint_list.lookup_increasing(0,1<<i)))
			while (len(pixel_states)<(self._led_depth<<3)):
				pixel_states.append(LEDSignCompilationPixel(0,None))
		else:
			self._led_depth=program._hardware._led_depth
			for i in range(self._led_depth<<3):
				pixel_states.append(LEDSignCompilationPixel(1<<i,program._keypoint_list.lookup_increasing(0,1<<i)))
		self._data=bytearray(program._duration*self._led_depth*24)
		self._max_offset=max(len(self._data)>>2,1)
		self._offset_divisor=max(6*self._led_depth,1)*60
		self._ctrl=(3*self._led_depth)|(len(self._data)<<6)
		for i in range(0,program._duration):
			for j in range(0,self._led_depth<<3):
				pixel=pixel_states[j]
				kp=pixel.kp
				if (kp is None):
					continue
				if (kp.end<=i):
					pixel.r=(kp.rgb>>16)&0xff
					pixel.g=(kp.rgb>>8)&0xff
					pixel.b=kp.rgb&0xff
					pixel.prev_r=(kp.rgb>>16)&0xff
					pixel.prev_g=(kp.rgb>>8)&0xff
					pixel.prev_b=kp.rgb&0xff
					kp=program._keypoint_list.lookup_increasing(kp._key+1,pixel.mask)
					pixel.kp=kp
					if (kp is None):
						continue
				t=max((i-kp.end+1)/kp.duration+1,0)
				pixel.r=round(pixel.prev_r+t*(((kp.rgb>>16)&0xff)-pixel.prev_r))
				pixel.g=round(pixel.prev_g+t*(((kp.rgb>>8)&0xff)-pixel.prev_g))
				pixel.b=round(pixel.prev_b+t*((kp.rgb&0xff)-pixel.prev_b))
			for j in range(0,self._led_depth):
				rveclo=0
				gveclo=0
				bveclo=0
				rvechi=0
				gvechi=0
				bvechi=0
				for k in range(0,4):
					l=k<<3
					pixel=pixel_states[j+k*self._led_depth]
					rveclo|=pixel.r<<l
					gveclo|=pixel.g<<l
					bveclo|=pixel.b<<l
					pixel=pixel_states[j+(k+4)*self._led_depth]
					rvechi|=pixel.r<<l
					gvechi|=pixel.g<<l
					bvechi|=pixel.b<<l
				rveclo=_bit_permute_step(rveclo,0x00aa00aa,7)
				gveclo=_bit_permute_step(gveclo,0x00aa00aa,7)
				bveclo=_bit_permute_step(bveclo,0x00aa00aa,7)
				rvechi=_bit_permute_step(rvechi,0x00aa00aa,7)
				gvechi=_bit_permute_step(gvechi,0x00aa00aa,7)
				bvechi=_bit_permute_step(bvechi,0x00aa00aa,7)
				rveclo=_bit_permute_step(rveclo,0x0000cccc,14)
				gveclo=_bit_permute_step(gveclo,0x0000cccc,14)
				bveclo=_bit_permute_step(bveclo,0x0000cccc,14)
				rvechi=_bit_permute_step(rvechi,0x0000cccc,14)
				gvechi=_bit_permute_step(gvechi,0x0000cccc,14)
				bvechi=_bit_permute_step(bvechi,0x0000cccc,14)
				rveclo=_bit_permute_step(rveclo,0x00f000f0,4)
				gveclo=_bit_permute_step(gveclo,0x00f000f0,4)
				bveclo=_bit_permute_step(bveclo,0x00f000f0,4)
				rvechi=_bit_permute_step(rvechi,0x00f000f0,4)
				gvechi=_bit_permute_step(gvechi,0x00f000f0,4)
				bvechi=_bit_permute_step(bvechi,0x00f000f0,4)
				rveclo=_bit_permute_step(rveclo,0x0000ff00,8)
				gveclo=_bit_permute_step(gveclo,0x0000ff00,8)
				bveclo=_bit_permute_step(bveclo,0x0000ff00,8)
				rvechi=_bit_permute_step(rvechi,0x0000ff00,8)
				gvechi=_bit_permute_step(gvechi,0x0000ff00,8)
				bvechi=_bit_permute_step(bvechi,0x0000ff00,8)
				k=i*self._led_depth*24+j*12
				self._data[k:k+12]=struct.pack("<III",rveclo,gveclo,bveclo)
				k+=12*self._led_depth
				self._data[k:k+12]=struct.pack("<III",rvechi,gvechi,bvechi)
		self._crc=LEDSignCRC(self._data).value

	def __repr__(self):
		return f"<LEDSignCompiledProgram size={len(self._data)} B>"

	def _upload_to_device(self,device):
		if (device._hardware._led_depth!=self._led_depth):
			raise LEDSignProgramError("Mismatched program hardware")
		result=LEDSignProtocol.process_packet(device._handle,LEDSignProtocol.PACKET_TYPE_PROGRAM_CHUNK_REQUEST,LEDSignProtocol.PACKET_TYPE_PROGRAM_SETUP,self._ctrl,self._crc)
		while (result[0]!=0xffffffff):
			if (not result[1]):
				time.sleep(0.02)
			else:
				LEDSignProtocol.process_extended_write(device._handle,self._data[result[0]:result[0]+result[1]])
			result=LEDSignProtocol.process_packet(device._handle,LEDSignProtocol.PACKET_TYPE_PROGRAM_CHUNK_REQUEST,LEDSignProtocol.PACKET_TYPE_PROGRAM_UPLOAD_STATUS)
		device._driver_program_offset_divisor=self._offset_divisor
		device._driver_program_max_offset=self._max_offset
		device._driver_info_sync_next_time=0
		device._program=None

	def _save_to_file(self,file_path):
		with open(file_path,"wb") as wf:
			wf.write(struct.pack("<II",self._ctrl,self._crc))
			wf.write(self._data)



class LEDSignProgramBuilder(object):
	COMMAND_SHORCUTS={
		"af": "after",
		"dt": "delta_time",
		"ed": "end",
		"hw": "hardware",
		"kp": "keypoint",
		"tm": "time"
	}
	_global_lock=threading.Lock()
	_current_instance=None

	__slots__=["program","time"]

	def __init__(self,program):
		if (not isinstance(program,LEDSignProgram) or not program._builder_ready):
			raise RuntimeError("Direct initialization of LEDSignProgramBuilder is not supported")
		self.program=program
		self.time=1

	def _change_lock(self,enable):
		if (enable):
			LEDSignProgramBuilder._global_lock.acquire()
			LEDSignProgramBuilder._current_instance=self
		else:
			LEDSignProgramBuilder._current_instance=None
			LEDSignProgramBuilder._global_lock.release()

	def _get_function_list(self):
		for k,v in LEDSignProgramBuilder.COMMAND_SHORCUTS.items():
			yield (k,getattr(self,"command_"+v))
		for k in dir(self):
			if (k.lower().startswith("command_")):
				yield (k[8:],getattr(self,k))

	def command_at(self,time):
		self.time=max(round(time*60),1)

	def command_after(self,time):
		self.time=max(self.time+round(time*60),1)

	def command_delta_time(self):
		return 1/60

	def command_time(self):
		return self.time/60

	def command_hardware(self):
		return self.program._hardware

	def command_keypoint(self,rgb,mask,duration=1/60,time=None):
		if (isinstance(rgb,int)):
			rgb&=0xffffff
		elif (isinstance(rgb,str) and len(rgb)==7 and rgb[0]=="#"):
			rgb=int(rgb[1:7],16)
		else:
			raise TypeError(f"Expected 'int' or 'hex-color', got '{rgb.__class__.__name__}'")
		if (not isinstance(mask,int)):
			raise TypeError(f"Expected 'int', got '{mask.__class__.__name__}'")
		if (isinstance(duration,int) or isinstance(duration,float)):
			duration=max(round(duration*60),1)
		else:
			raise TypeError(f"Expected 'int' or 'float', got '{duration.__class__.__name__}'")
		if (time is None):
			time=self.time
		elif (isinstance(end,int) or isinstance(end,float)):
			time=max(round(time*60),1)
		else:
			raise TypeError(f"Expected 'int' or 'float', got '{time.__class__.__name__}'")
		self.program._add_raw_keypoint(rgb,time,duration,mask,(sys._getframe(1) if hasattr(sys,"_getframe") else None))

	def command_end(self):
		self.program._duration=self.time

	def command_rgb(self,r,g,b):
		r=min(max(round(r),0),255)
		g=min(max(round(g),0),255)
		b=min(max(round(b),0),255)
		return (r<<16)+(g<<8)+b

	def command_hsv(self,h,s,v):
		h=(h%360)/60
		s=min(max(s,0),1)
		v*=255
		if (s==0):
			return min(max(round(v),0),255)*0x010101
		i=int(h)
		s*=v
		f=s*(h-i)
		p=min(max(round(v-s),0),255)
		q=min(max(round(v-f),0),255)
		t=min(max(round(v-s+f),0),255)
		if (not i):
			return (v<<16)+(t<<8)+p
		if (i==1):
			return (q<<16)+(v<<8)+p
		if (i==2):
			return (p<<16)+(v<<8)+t
		if (i==3):
			return (p<<16)+(q<<8)+v
		if (i==4):
			return (t<<16)+(p<<8)+v
		return (v<<16)+(p<<8)+q

	@staticmethod
	def instance():
		return LEDSignProgramBuilder._current_instance



class LEDSignSelector(object):
	@staticmethod
	def get_center(mask=-1,hardware=None):
		if (hardware is None):
			hardware=LEDSignProgramBuilder.instance().program._hardware
		cx=0
		cy=0
		cn=0
		for i,xy in enumerate(hardware._pixels):
			if (xy is not None and (mask&1)):
				cx+=xy[0]
				cy+=xy[1]
				cn+=1
			mask>>=1
		cn+=not cn
		return (cx/cn,cy/cn)

	@staticmethod
	def get_pixels(mask=-1,letter=None,hardware=None):
		if (hardware is None):
			hardware=LEDSignProgramBuilder.instance().program._hardware
		if (letter is not None):
			mask&=LEDSignSelector.select_letter(letter,hardware=hardware)
		m=1
		for i,xy in enumerate(hardware._pixels):
			if (xy is not None and (mask&m)):
				yield (xy[0],xy[1],m)
			m<<=1

	@staticmethod
	def get_letter_mask(index,hardware=None):
		if (hardware is None):
			hardware=LEDSignProgramBuilder.instance().program._hardware
		for i in range(0,8):
			if (not hardware._raw_config[i]):
				continue
			if (not index):
				return ((1<<((i+1)*hardware._led_depth))-(1<<(i*hardware._led_depth)))&hardware._mask
			index-=1
		raise IndexError("Letter index out of range")

	@staticmethod
	def get_letter_masks(hardware=None):
		if (hardware is None):
			hardware=LEDSignProgramBuilder.instance().program._hardware
		for i in range(0,8):
			if (not hardware._raw_config[i]):
				continue
			yield (i,chr(hardware._raw_config[i]),((1<<((i+1)*hardware._led_depth))-(1<<(i*hardware._led_depth)))&hardware._mask)

	@staticmethod
	def get_circle_mask(cx,cy,r,hardware=None):
		if (hardware is None):
			hardware=LEDSignProgramBuilder.instance().program._hardware
		r*=r
		out=0
		for i,xy in enumerate(hardware._pixels):
			if (xy is not None and (xy[0]-cx)**2+(xy[1]-cy)**2<=r):
				out|=1<<i
		return out



class LEDSignProgramKeypoint(object):
	__slots__=["rgb","end","duration","mask","_frame","_key","_subtree_mask","_parent","_color","_nodes"]

	def __init__(self,rgb,end,duration,mask,frame):
		self.rgb=rgb
		self.end=end
		self.duration=duration
		self.mask=mask
		self._frame=("<unknown>" if frame is None else f"{frame.f_code.co_filename}:{frame.f_lineno}({frame.f_code.co_name})")
		self._key=None
		self._subtree_mask=mask
		self._parent=None
		self._color=0
		self._nodes=[None,None]

	def __repr__(self):
		return f"<LEDSignProgramKeypoint color=#{self.rgb:06x} duration={self.duration/60:.3f}s end={self.end/60:.3f}s mask={self.mask:x}>"



class LEDSignKeypointList(object):
	def __init__(self):
		self.root=None
		self._index=0

	def _rotate_subtree(self,x,dir):
		y=x._parent
		z=x._nodes[dir^1]
		x._nodes[dir^1]=z._nodes[dir]
		if (z._nodes[dir]):
			z._nodes[dir]._parent=x
		z._nodes[dir]=x
		x._parent=z
		z._parent=y
		x._subtree_mask=x.mask
		if (x._nodes[0] is not None):
			x._subtree_mask|=x._nodes[0]._subtree_mask
		if (x._nodes[1] is not None):
			x._subtree_mask|=x._nodes[1]._subtree_mask
		z._subtree_mask=z.mask|x._subtree_mask
		if (z._nodes[dir^1] is not None):
			z._subtree_mask|=z._nodes[dir^1]._subtree_mask
		if (y is None):
			self.root=z
		else:
			dir=(x==y._nodes[1])
			y._nodes[dir]=z
			y._subtree_mask=y.mask|z._subtree_mask
			if (y._nodes[dir^1] is not None):
				y._subtree_mask|=y._nodes[dir^1]._subtree_mask

	def clear(self):
		self.root=None

	def lookup_decreasing(self,key,mask):
		x=self.root
		while (x is not None and (x._key!=key or not (x.mask&mask))):
			if (key>x._key):
				y=x._nodes[1]
				if (y is not None and (y._subtree_mask&mask)):
					x=y
					continue
				if (x.mask&mask):
					return x
			y=x._nodes[0]
			if (y is not None and (y._subtree_mask&mask)):
				x=y
				continue
			while (True):
				y=x
				x=x._parent
				if (x is None):
					return None
				if (y==x._nodes[1]):
					break
			key=x._key
		return x

	def lookup_increasing(self,key,mask):
		x=self.root
		while (x is not None and (x._key!=key or not (x.mask&mask))):
			if (key<x._key):
				y=x._nodes[0]
				if (y is not None and (y._subtree_mask&mask)):
					x=y
					continue
				if (x.mask&mask):
					return x
			y=x._nodes[1]
			if (y is not None and (y._subtree_mask&mask)):
				x=y
				continue
			while (True):
				y=x
				x=x._parent
				if (x is None):
					return None
				if (y==x._nodes[0]):
					break
			key=x._key
		return x

	def insert(self,x):
		x._key=(x.end<<44)|self._index
		x._parent=None
		x._nodes=[None,None]
		self._index+=1
		if (self.root is None):
			x._color=0
			self.root=x
			return
		x._color=1
		y=self.root
		while (y._nodes[y._key<x._key] is not None):
			y=y._nodes[y._key<x._key]
		x._parent=y
		y._nodes[y._key<x._key]=x
		while (y is not None and y._color):
			y._subtree_mask=y.mask
			if (y._nodes[0] is not None):
				y._subtree_mask|=y._nodes[0]._subtree_mask
			if (y._nodes[1] is not None):
				y._subtree_mask|=y._nodes[1]._subtree_mask
			z=y._parent
			if (z is None):
				y._color=0
				break
			z._subtree_mask=z.mask
			if (z._nodes[0] is not None):
				z._subtree_mask|=z._nodes[0]._subtree_mask
			if (z._nodes[1] is not None):
				z._subtree_mask|=z._nodes[1]._subtree_mask
			dir=(y==z._nodes[0])
			w=z._nodes[dir]
			if (w is None or not w._color):
				if (x==y._nodes[dir]):
					self._rotate_subtree(y,dir^1)
					y=z._nodes[dir^1]
				self._rotate_subtree(z,dir)
				y._color=0
				z._color=1
				y=z._parent._parent
				break
			y._color=0
			z._color=1
			w._color=0
			x=z
			y=x._parent
		while (y is not None):
			y._subtree_mask=y.mask
			if (y._nodes[0] is not None):
				y._subtree_mask|=y._nodes[0]._subtree_mask
			if (y._nodes[1] is not None):
				y._subtree_mask|=y._nodes[1]._subtree_mask
			y=y._parent

	def iterate(self,mask):
		entry=self.lookup_increasing(0,mask)
		while (entry is not None):
			yield entry
			entry=self.lookup_increasing(entry._key+1,mask)



class LEDSignProgram(object):
	__slots__=["_hardware","_duration","_keypoint_list","_load_parameters","_builder_ready","_has_error"]

	def __init__(self,device,file_path=None):
		if (not isinstance(device,LEDSign)):
			raise TypeError(f"Expected 'LEDSign', got '{device.__class__.__name__}'")
		if (file_path is not None and not isinstance(file_path,str)):
			raise TypeError(f"Expected 'str', got '{file_path.__class__.__name__}'")
		self._hardware=device._hardware
		self._duration=1
		self._keypoint_list=LEDSignKeypointList()
		self._load_parameters=None
		self._builder_ready=False
		self._has_error=False
		if (file_path is not None):
			self._load_from_file(file_path)

	def __repr__(self):
		return f"<LEDSignProgram{('[unloaded]' if self._load_parameters is not None else '')} hardware={self._hardware.get_string()} duration={self._duration/60:.3f}s>"

	def __call__(self,func):
		self._builder_ready=True
		builder=LEDSignProgramBuilder(self)
		self._builder_ready=False
		builder._change_lock(True)
		namespace=func.__globals__
		old_namespace={}
		for k,v in builder._get_function_list():
			if (k in namespace):
				old_namespace[k]=namespace[k]
			namespace[k]=v
		try:
			func()
			self.verify()
		except:
			self._has_error=True
		finally:
			for k,_ in builder._get_function_list():
				if (k in old_namespace):
					namespace[k]=old_namespace[k]
				else:
					del namespace[k]
			builder._change_lock(False)
		return self

	def _add_raw_keypoint(self,rgb,end,duration,mask,frame):
		mask&=self._hardware._mask
		if (not mask):
			return
		kp=LEDSignProgramKeypoint(rgb,end,duration,mask,frame)
		self._keypoint_list.insert(kp)

	def _load_from_file(self,file_path):
		size=os.stat(file_path).st_size
		if (size<8 or (size&3)):
			raise LEDSignProgramError("Invalid program")
		with open(file_path,"rb") as rf:
			ctrl,crc=struct.unpack("<II",rf.read(8))
			data=rf.read()
		if ((ctrl&0xff)%3 or size!=((ctrl>>8)<<2)+8 or crc!=LEDSignCRC(data).value):
			raise LEDSignProgramError("Invalid program")
		if (((self._hardware._pixel_count+7)>>3)!=(ctrl&0xff)//3):
			raise LEDSignProgramError("Invalid program")
		self._duration=(ctrl>>9)//max(ctrl&0xff,1)
		parser=LEDSignProgramParser(self,(ctrl&0xff)//3,True)
		parser.update(data)
		parser.terminate()

	def compile(self,bypass_errors=False):
		self.load()
		if (self._has_error and not bypass_errors):
			raise LEDSignProgramError("Unresolved program errors")
		return LEDSignCompiledProgram(self,False)

	def save(self,file_path,bypass_errors=False):
		self.load()
		if (self._has_error and not bypass_errors):
			raise LEDSignProgramError("Unresolved program errors")
		LEDSignCompiledProgram(self,True)._save_to_file(file_path)

	def load(self):
		if (self._load_parameters is None):
			return
		load_parameters=self._load_parameters
		self._load_parameters=None
		device=load_parameters[0]()
		if (device is None):
			self._has_error=True
			raise LEDSignProtocolError("Device disconnected")
		if ((load_parameters[1]&0xff)//3!=self._hardware._led_depth):
			self._has_error=True
			raise LEDSignProgramError("Mismatched program hardware")
		parser=LEDSignProgramParser(self,(load_parameters[1]&0xff)//3,False)
		program_size=(load_parameters[1]>>8)<<2
		chunk_size=min(max(program_size,64),65536)
		chunk_size-=chunk_size%12
		received_crc=LEDSignCRC()
		offset=0
		while (offset<program_size):
			availbale_chunk_size=LEDSignProtocol.process_packet(device._handle,LEDSignProtocol.PACKET_TYPE_PROGRAM_CHUNK_RESPONSE,LEDSignProtocol.PACKET_TYPE_PROGRAM_CHUNK_REQUEST,offset,chunk_size)[0]
			chunk=LEDSignProtocol.process_extended_read(device._handle,availbale_chunk_size)
			received_crc.update(chunk)
			parser.update(chunk)
			offset+=availbale_chunk_size
		if (received_crc.value!=load_parameters[2]):
			self._program._keypoint_list.clear()
			self._has_error=True
			raise LEDSignProgramError("Mismatched program checksum")
		parser.terminate()

	def get_keypoints(self,mask=-1):
		return self._keypoint_list.iterate(mask)

	def verify(self):
		self._has_error=False
		kp=self._keypoint_list.lookup_increasing(0,-1)
		while (kp is not None):
			start=kp.end-kp.duration
			if (start<0):
				print(f"Keypoint overlap: ({-start/60:.3f}s)\n  <timeline_start>\n  {kp._frame}")
				self._has_error=True
			entry=self._keypoint_list.lookup_decreasing(kp._key-1,kp.mask)
			while (entry is not None and entry.end>start):
				if (entry!=kp):
					print(f"Keypoint overlap: ({(entry.end-start)/60:.3f}s)\n  {entry._frame}\n  {kp._frame}")
					self._has_error=True
				entry=self._keypoint_list.lookup_decreasing(entry._key-1,kp.mask)
			kp=self._keypoint_list.lookup_increasing(kp._key+1,-1)

	@staticmethod
	def _create_unloaded_from_device(device,ctrl,crc):
		out=LEDSignProgram(device)
		out._duration=(ctrl>>9)//max(ctrl&0xff,1)
		if (ctrl>>8):
			out._load_parameters=(weakref.ref(device),ctrl,crc)
		return out



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
