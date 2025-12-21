import ctypes
import os
import struct



__all__=["LEDSignProtocolBackendWindows","LEDSignProtocolBackendLinux"]



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

	def __init__(self) -> None:
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
		self.WinUsb_GetAssociatedInterface=ctypes.windll.winusb.WinUsb_GetAssociatedInterface
		self.WinUsb_GetAssociatedInterface.argtypes=(ctypes.wintypes.HANDLE,ctypes.wintypes.CHAR,ctypes.POINTER(ctypes.wintypes.HANDLE))
		self.WinUsb_GetAssociatedInterface.restype=ctypes.wintypes.BOOL
		self.winusb_registry_guid_ref=ctypes.byref(GUID.from_buffer(bytearray(b"\x58\x30\xf5\xfc\x7b\x99\x21\x4b\xaf\xd6\xe5\x65\x04\x39\x23\xc1")))
		self.GetLastError=ctypes.windll.kernel32.GetLastError
		self.GetLastError.argtypes=tuple()
		self.GetLastError.restype=ctypes.wintypes.DWORD

	def enumerate(self) -> list[str]:
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

	def open(self,path:str) -> tuple[int,int,int]:
		handle=self.CreateFileA(path.encode("utf-8"),LEDSignProtocolBackendWindows.GENERIC_WRITE|LEDSignProtocolBackendWindows.GENERIC_READ,LEDSignProtocolBackendWindows.FILE_SHARE_READ|LEDSignProtocolBackendWindows.FILE_SHARE_WRITE,0,LEDSignProtocolBackendWindows.OPEN_EXISTING,LEDSignProtocolBackendWindows.FILE_ATTRIBUTE_NORMAL|LEDSignProtocolBackendWindows.FILE_FLAG_OVERLAPPED,0)
		if (handle==0xffffffffffffffff):
			raise OSError("Device already in use")
		winusb_handle=ctypes.wintypes.HANDLE(0)
		if (not self.WinUsb_Initialize(handle,ctypes.byref(winusb_handle))):
			self.CloseHandle(handle)
			raise OSError("Device already in use")
		interface_handle=ctypes.wintypes.HANDLE(0)
		if (not self.WinUsb_GetAssociatedInterface(winusb_handle,0,ctypes.byref(interface_handle))):
			self.WinUsb_Free(winusb_handle.value)
			self.CloseHandle(handle)
			raise OSError("Device error")
		return (handle,winusb_handle.value,interface_handle.value)

	def close(self,handles:tuple[int,int,int]) -> None:
		self.WinUsb_Free(handles[2])
		self.WinUsb_Free(handles[1])
		self.CloseHandle(handles[0])

	def transfer_ctrl(self,handles:tuple[int,int,int],type:int,value:int,index:int,length:int) -> None|bytearray:
		buffer=(ctypes.wintypes.CHAR*length)()
		transferred=ctypes.c_ulong(0)
		if (not self.WinUsb_ControlTransfer(handles[1],0xc0|(type<<8)|(value<<16)|(index<<32)|(length<<48),buffer,length,ctypes.byref(transferred),0)):
			return None
		return bytearray(buffer)[:length]

	def transfer_bulk_out(self,handles:tuple[int,int,int],endpoint:int,data:bytes) -> bool:
		data=bytearray(data)
		transferred=ctypes.c_ulong(0)
		return self.WinUsb_WritePipe(handles[1+(endpoint>3)],endpoint&0x7f,(ctypes.c_char*len(data)).from_buffer(data),len(data),ctypes.byref(transferred),0) and transferred.value==len(data)

	def transfer_bulk_in(self,handles:tuple[int,int,int],endpoint:int,length:int) -> None|bytearray:
		out=(ctypes.c_char*length)()
		transferred=ctypes.c_ulong(0)
		return (None if not self.WinUsb_ReadPipe(handles[1+(endpoint>3)],(endpoint&0x7f)|0x80,out,length,ctypes.byref(transferred),0) else bytearray(out)[:transferred.value])



class LEDSignProtocolBackendLinux(object):
	USBDEVFS_BULK=0xc0185502
	USBDEVFS_CLAIMINTERFACE=0x8004550f
	USBDEVFS_CONTROL=0xc0185500

	def __init__(self) -> None:
		import ctypes.util
		self.ioctl=ctypes.CDLL(ctypes.util.find_library("c"),use_errno=True).ioctl
		self.ioctl.argtypes=(ctypes.c_int,ctypes.c_ulong,ctypes.c_char_p)
		self.ioctl.restype=ctypes.c_int

	def enumerate(self) -> list[str]:
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

	def open(self,path:str) -> int:
		handle=os.open(path,os.O_RDWR)
		return (None if self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_CLAIMINTERFACE,struct.pack("<I",0))<0 or self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_CLAIMINTERFACE,struct.pack("<I",1))<0 else handle)

	def close(self,handle:int) -> None:
		os.close(handle)

	def transfer_ctrl(self,handle:int,type:int,value:int,index:int,length:int) -> None|bytearray:
		buffer=(ctypes.c_uint8*length)()
		if (self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_CONTROL,struct.pack("<BBHHHI4xQ",0xc0,type,value,index,length,3000,ctypes.addressof(buffer)))!=length):
			return None
		return bytearray(buffer)[:length]

	def transfer_bulk_out(self,handle:int,endpoint:int,data:bytes) -> bool:
		data=bytearray(data)
		return self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_BULK,struct.pack("<III4xQ",endpoint&0x7f,len(data),3000,ctypes.addressof((ctypes.c_uint8*len(data)).from_buffer(data))))==len(data)

	def transfer_bulk_in(self,handle:int,endpoint:int,length:int) -> None|bytearray:
		out=(ctypes.c_uint8*length)()
		ret=self.ioctl(handle,LEDSignProtocolBackendLinux.USBDEVFS_BULK,struct.pack("<III4xQ",(endpoint&0x7f)|0x80,length,3000,ctypes.addressof(out)))
		return (None if ret<0 else bytearray(out)[:ret])
