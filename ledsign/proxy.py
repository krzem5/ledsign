from ledsign.backend import LEDSignProtocolBackendWindows,LEDSignProtocolBackendLinux
import base64
import hashlib
import socket
import struct
import sys
import threading



__all__=["LEDSignProxyServer","LEDSignBackendProxy","LEDSignProxyError","LEDSignProtocolError"]



class LEDSignProxyError(Exception):
	"""
	Raised during any proxy-related exception.
	"""



class LEDSignProtocolError(Exception):
	"""
	Raised during any encountered protocol error.
	"""



class LEDSignProxyServerDeviceHandleWrapper(object):
	def __init__(self,id_,file_path,handle):
		self.id_=id_
		self.file_path=file_path
		self.handle=handle
		self.marked=True



class LEDSignProxyServer(object):
	PROXY_PORT=9100

	def __init__(self) -> None:
		self._backend=(LEDSignProtocolBackendWindows if sys.platform=="win32" else LEDSignProtocolBackendLinux)()
		self._server_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self._server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		self._server_socket.bind(("127.0.0.1",LEDSignProxyServer.PROXY_PORT))
		self._server_socket.listen(5)
		self._device_handles_by_id={}
		self._device_handles_by_file_path={}
		thr=threading.Thread(target=self._thread)
		thr.daemon=True
		thr.start()

	def _process_packet(self,data):
		if (len(data)<6 or data[0]&1):
			return data[:2]
		if (data[0]==0x00 and len(data)==6):
			return data[:2]+self._process_enumerate_packet()
		if (data[0]==0x02 and len(data)==11):
			return data[:2]+self._process_transfer_ctrl(data)
		if (data[0]==0x04):
			return data[:2]+self._process_transfer_bulk_out(data)
		if (data[0]==0x06):
			return data[:2]+self._process_transfer_bulk_in(data)
		return data[:2]

	def _process_enumerate_packet(self):
		for file_path in self._backend.enumerate():
			if (file_path in self._device_handles_by_file_path):
				self._device_handles_by_file_path[file_path].marked=True
				continue
			handle=self._backend.open(file_path)
			if (handle is None):
				continue
			next_id=1
			while (next_id in self._device_handles_by_id):
				next_id+=1
			wrapper=LEDSignProxyServerDeviceHandleWrapper(next_id,file_path,handle)
			self._device_handles_by_id[next_id]=wrapper
			self._device_handles_by_file_path[file_path]=wrapper
		out=b""
		for wrapper in list(self._device_handles_by_file_path.values()):
			if (not wrapper.marked):
				self._remove_handle(wrapper)
				continue
			wrapper.marked=False
			out+=struct.pack("<I",wrapper.id_)
		return struct.pack("<H",len(self._device_handles_by_file_path))+out

	def _process_transfer_ctrl(self,data):
		type,id_,value,index,length=struct.unpack("<BIHHB",data[1:])
		wrapper=self._device_handles_by_id.get(id_,None)
		if (wrapper is None):
			return b"\x01"
		ret=self._backend.transfer_ctrl(wrapper.handle,type,value,index,length)
		if (ret is None):
			return b"\x01"
		return b"\x00"+ret

	def _process_transfer_bulk_out(self,data):
		endpoint,id_=struct.unpack("<BI",data[1:6])
		wrapper=self._device_handles_by_id.get(id_,None)
		if (wrapper is None):
			return b"\x01"
		return bytearray([not self._backend.transfer_bulk_out(wrapper.handle,endpoint,data[6:])])

	def _process_transfer_bulk_in(self,data):
		endpoint,id_,length=struct.unpack("<BIH",data[1:])
		wrapper=self._device_handles_by_id.get(id_,None)
		if (wrapper is None):
			return b"\x01"
		ret=self._backend.transfer_bulk_in(wrapper.handle,endpoint,length)
		return (b"\x01" if ret is None else b"\x00"+ret)

	def _remove_handle(self,wrapper):
		del self._device_handles_by_id[wrapper.id_]
		del self._device_handles_by_file_path[wrapper.file_path]
		self._backend.close(wrapper.handle)

	def _thread(self):
		while (True):
			cs=self._server_socket.accept()[0]
			cs.settimeout(0.5)
			thr=threading.Thread(target=self._handle_http_connection,args=(cs,),kwargs={})
			thr.daemon=True
			thr.start()

	def _handle_http_connection(self,cs):
		try:
			buffer=cs.recv(16384)
			cs.settimeout(None)
			if (buffer==b"\xffraw\xff"):
				cs.sendall(buffer)
				while (True):
					buffer=cs.recv(16384)
					if (not buffer):
						return
					cs.sendall(self._process_packet(buffer))
				return
			if (not buffer.startswith(b"GET / HTTP/1.1")):
				return
			ws_key=None
			prev_line_was_empty=False
			for line in buffer.split(b"\r\n"):
				if (not line):
					if (prev_line_was_empty):
						break
					prev_line_was_empty=True
					continue
				prev_line_was_empty=False
				line=line.strip().split(b":")
				if (len(line)!=2):
					continue
				key,value=line[0].lower(),line[1].strip()
				if (key==b"sec-websocket-key"):
					ws_key=value
				elif (key==b"connection" and value.lower()!=b"upgrade"):
					return
				elif (key==b"upgrade" and value.lower()!=b"websocket"):
					return
			if (ws_key is None):
				return
			cs.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "+base64.b64encode(hashlib.sha1(ws_key+b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())+b"\r\n\r\n")
			current_frame_type=-1
			current_frame_data=None
			while (True):
				buffer=cs.recv(16384)
				if (not buffer):
					return
				i=0
				while (i+1<len(buffer)):
					if (buffer[i]&0x70):
						return
					frame_is_last=buffer[i]>>7
					frame_type=buffer[i]&0x0f
					frame_masking_key_present=buffer[i+1]>>7
					frame_length=buffer[i+1]&0x7f
					i+=2
					if (frame_length==126):
						i+=2
						if (i>len(buffer)):
							return
						frame_length=(buffer[i-2]<<8)|buffer[i-1]
					elif (frame_length==127):
						return
					mask=b"\x00\x00\x00\x00"
					if (frame_masking_key_present):
						mask=buffer[i:i+4]
						i+=4
					if (i+frame_length>len(buffer)):
						return
					if (frame_type==0):
						if (current_frame_type==-1):
							return
					elif (frame_type==1 or frame_type==2):
						if (current_frame_type!=-1):
							return
						current_frame_type=frame_type
						current_frame_data=bytearray()
					else:
						return
					j=len(current_frame_data)
					current_frame_data+=buffer[i:i+frame_length]
					for k in range(0,frame_length):
						current_frame_data[j+k]^=mask[k&3]
					i+=frame_length
					if (not frame_is_last):
						continue
					data=self._process_packet(current_frame_data)
					current_frame_type=-1
					current_frame_data=None
					if (len(data)<126):
						packet=bytearray([
							0x82,
							len(data)
						])+data
					else:
						packet=bytearray([
							0x82,
							126,
							len(data)>>8,
							len(data)&0xff
						])+data
					cs.sendall(packet)
		except BrokenPipeError:
			pass
		finally:
			cs.close()




class LEDSignBackendProxy(object):
	def __init__(self) -> None:
		self._client_socket=None

	def enumerate(self) -> list[str]:
		data=self._execute(b"\x00\x00\x00\x00\x00\x00")
		length=struct.unpack("<H",data[2:4])[0]
		return [f"proxy/#{e:08x}" for e in struct.unpack(f"<{length}I",data[4:4+4*length])]

	def open(self,path:str) -> int:
		device_id=int(path[7:],16)
		ret=self._execute(struct.pack("<BBIH2xB",0x02,0x52,device_id,0x5453,5))
		if (ret[2] or len(ret)!=8 or bytes(ret[3:])!=b"reset"):
			raise LEDSignProtocolError("Unable to reset device, Python API disabled")
		return device_id

	def close(self,handle:int) -> None:
		pass

	def io_read_write(self,handle:int,packet:bytes) -> bytearray:
		ret=self._execute(struct.pack("<BBI",0x04,0x04,handle)+packet)
		if (ret[2]):
			raise LEDSignProtocolError("Write to endpoint 04h failed")
		ret=self._execute(struct.pack("<BBIH",0x06,0x04,handle,64))
		if (ret[2] or len(ret)<5):
			raise LEDSignProtocolError("Read from endpoint 84h failed")
		return ret[3:]

	def io_bulk_read(self,handle:int,size:int) -> bytearray:
		ret=self._execute(struct.pack("<BBIH",0x06,0x05,handle,size))
		if (ret[2] or len(ret)!=size+3):
			raise LEDSignProtocolError("Read from endpoint 85h failed")
		return ret[3:]

	def io_bulk_write(self,handle:int,data:bytearray) -> None:
		if (self._execute(struct.pack("<BBI",0x04,0x05,handle)+data)[2]):
			raise LEDSignProtocolError("Write to endpoint 04h failed")

	def _execute(self,data):
		if (self._client_socket is None):
			self._client_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			try:
				self._client_socket.connect(("127.0.0.1",LEDSignProxyServer.PROXY_PORT))
			except ConnectionRefusedError:
				raise LEDSignProxyError("Unable to connect to proxy server, run 'ledsign -z' to start one")
			self._client_socket.sendall(b"\xffraw\xff")
			self._client_socket.recv(5)
		self._client_socket.sendall(data)
		return self._client_socket.recv(16384)



if (__name__=="__main__"):
	LEDSignProxyServer()
	input()
