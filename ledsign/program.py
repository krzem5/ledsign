from ledsign.keypoint_list import LEDSignKeypoint,LEDSignKeypointList
import ledsign.device
import threading
import weakref



__all__=["LEDSignProgramError","LEDSignProgram","LEDSignProgramBuilder"]



LEDSignProgramError=type("LEDSignProgramError",(Exception,),{})



class LEDSignProgram(object):
	__slots__=["_hardware","_duration","_keypoint_list","_load_parameters","_builder_ready","_has_error"]

	def __init__(self,device,file_path=None):
		if (not isinstance(device,ledsign.device.LEDSign)):
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
		kp=LEDSignKeypoint(rgb,end,duration,mask,frame)
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
