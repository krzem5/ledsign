from collections.abc import Callable
from ledsign.checksum import LEDSignCRC
from ledsign.protocol import LEDSignProtocol
import ledsign.program
import struct
import time



__all__=["LEDSignProgramParser","LEDSignCompiledProgram"]



def _bit_permute_step(a,b,c):
	t=((a>>c)^a)&b
	return (a^t)^(t<<c)



class LEDSignProgramParser(object):
	MAX_LINE_EXTRACTION_ERROR=2

	__slots__=["_program","_frame_length","_offset","_stride","_pixel_prev_states","_pixel_curr_states","_pixel_update_stack","_pixel_update_stack_length","_pixel_masks"]

	def __init__(self,program:"LEDSignProgram",frame_length:int,is_compressed:bool) -> None:
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

	def update(self,data:bytearray) -> None:
		for i in range(0,len(data),12):
			gvec,rvec,bvec=struct.unpack("<III",data[i:i+12])
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

	def terminate(self) -> None:
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

	def __init__(self,mask:int,kp:"LEDSignKeypoint"):
		self.r=0
		self.g=0
		self.b=0
		self.prev_r=0
		self.prev_g=0
		self.prev_b=0
		self.mask=mask
		self.kp=kp



class LEDSignCompiledProgram(object):
	"""
	Represents a compiled :py:class:`LEDSignProgram` object, returned by :py:func:`LEDSignProgram.compile`.
	"""

	__slots__=["_data","_led_depth","_max_offset","_offset_divisor","_ctrl","_crc"]

	def __init__(self,program:"LEDSignProgram",is_compressed:bool) -> None:
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
				self._data[k:k+12]=struct.pack("<III",gveclo,rveclo,bveclo)
				k+=12*self._led_depth
				self._data[k:k+12]=struct.pack("<III",gvechi,rvechi,bvechi)
		self._crc=LEDSignCRC(self._data).value

	def __repr__(self) -> str:
		return f"<LEDSignCompiledProgram size={len(self._data)} B>"

	def _upload_to_device(self,device:"LEDSign",callback:Callable[[float,bool],None]|None=None) -> None:
		if (device._hardware._led_depth!=self._led_depth):
			raise ledsign.program.LEDSignProgramError("Mismatched program hardware")
		result=LEDSignProtocol.process_packet(device._handle,LEDSignProtocol.PACKET_TYPE_PROGRAM_CHUNK_REQUEST_DEVICE,LEDSignProtocol.PACKET_TYPE_PROGRAM_SETUP,self._ctrl,self._crc)
		clear_progress_active=True
		prev_clear_progress=0
		if (callback is not None):
			callback(0.0,False)
		while (result[0]!=0xffffffff):
			if (not result[1]):
				if (not clear_progress_active):
					time.sleep(0.02)
			else:
				if (clear_progress_active):
					clear_progress_active=False
				if (callback is not None):
					callback(min(result[0]/len(self._data),1.0),True)
				LEDSignProtocol.process_extended_write(device._handle,self._data[result[0]:result[0]+result[1]])
			result=LEDSignProtocol.process_packet(device._handle,LEDSignProtocol.PACKET_TYPE_PROGRAM_CHUNK_REQUEST_DEVICE,LEDSignProtocol.PACKET_TYPE_PROGRAM_UPLOAD_STATUS)
			if (clear_progress_active and callback is not None and result[2]!=prev_clear_progress):
				prev_clear_progress=result[2]
				callback(min(result[2]/len(self._data),1.0),False)
		if (callback is not None):
			callback(1.0,True)
		device._driver_program_offset_divisor=self._offset_divisor
		device._driver_info_sync_next_time=0
		device._program=None

	def _save_to_file(self,file_path:str) -> None:
		with open(file_path,"wb") as wf:
			wf.write(struct.pack("<II",self._ctrl,self._crc))
			wf.write(self._data)
