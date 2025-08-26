from ledsign.program import LEDSignProgramBuilder
from ledsign.protocol import LEDSignProtocol
import array



__all__=["LEDSignHardware","LEDSignSelector"]



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
		return f"<LEDSignHardware config={self.get_string()} pixels={self._pixel_count}>"

	def get_string(self):
		return "["+" ".join([f"{e:02x}" for e in self._raw_config])+"]"



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
