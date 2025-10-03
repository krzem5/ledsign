from collections.abc import Iterator
from ledsign.program import LEDSignProgramBuilder
from ledsign.protocol import LEDSignProtocol
import array



__all__=["LEDSignHardware","LEDSignSelector"]



class LEDSignHardware(object):
	"""
	Read-only representation of a :py:class:`LEDSign` device's hardware, returned by :py:func:`LEDSign.get_hardware()`.
	"""

	SCALE=1/768

	__slots__=["_raw_config","_led_depth","_pixels","_pixel_count","_max_x","_max_y","_mask"]

	def __init__(self,handle,config) -> None:
		if (not isinstance(config,bytes) or len(config)!=8):
			raise TypeError("Direct initialization of LEDSignHardware is not supported")
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
				length,width=LEDSignProtocol.process_packet(handle,LEDSignProtocol.PACKET_TYPE_HARDWARE_DATA_RESPONSE,LEDSignProtocol.PACKET_TYPE_HARDWARE_DATA_REQUEST,key)
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

	def __repr__(self) -> str:
		return f"<LEDSignHardware config={self.get_string()} pixels={self._pixel_count}>"

	def get_raw(self) -> bytes:
		"""
		Returns the raw, 8-byte hardware configuration sequence returned by the device.
		"""
		return self._raw_config

	def get_string(self) -> str:
		"""
		Returns a pretty-printed version of the raw device hardware configuration returned by :py:func:`get_raw`.
		"""
		return "["+" ".join([f"{e:02x}" for e in self._raw_config])+"]"

	def get_user_string(self) -> str:
		"""
		Returns a user-friendly string identifying the device's hardware configuration.
		"""
		return bytearray([e for e in self._raw_config if e]).decode("utf-8")



class LEDSignSelector(object):
	"""
	This static class contains several common pattern generators, to be used within a :py:class:`LEDSignProgramBuilder` context.

	Every method accepts an optional :python:`hardware` argument, which when omitted will default to the one used by the current :py:class:`LEDSignProgramBuilder` instance (if a program builder is currently active).
	"""
	@staticmethod
	def _check_hardware(hardware:LEDSignHardware|None) -> LEDSignHardware:
		if (hardware is None):
			builder=LEDSignProgramBuilder.instance()
			if (builder is not None):
				hardware=builder.program._hardware
		if (not isinstance(hardware,LEDSignHardware)):
			raise TypeError(f"Expected 'LEDSignHardware', got '{hardware.__class__.__name__}'")
		return hardware

	@staticmethod
	def get_mask(hardware:LEDSignHardware|None=None) -> int:
		"""
		Returns a mask selecting all pixels.
		"""
		return LEDSignSelector._check_hardware(hardware)._mask

	@staticmethod
	def get_led_depth(hardware:LEDSignHardware|None=None) -> int:
		"""
		Returns the longest LED chain present in the current hardware configuration.
		"""
		return LEDSignSelector._check_hardware(hardware)._led_depth

	@staticmethod
	def get_bounding_box(mask:int=-1,hardware:LEDSignHardware|None=None) -> tuple[float,float,float,float]:
		"""
		Returns the bounding box :python:`(sx, sy, ex, ey)` of all pixels selected by :python:`mask`. If no mask is given, the bounding box of all pixels is computed.
		"""
		hardware=LEDSignSelector._check_hardware(hardware)
		if (not isinstance(mask,int)):
			raise TypeError(f"Expected 'int', got '{mask.__class__.__name__}'")
		out=[0.0,0.0,0.0,0.0]
		is_first=True
		for i,xy in enumerate(hardware._pixels):
			if (xy is not None and (mask&1)):
				x,y=xy
				if (is_first):
					is_first=False
					out[0]=x
					out[1]=y
					out[2]=x
					out[3]=y
				else:
					out[0]=min(out[0],x)
					out[1]=min(out[1],y)
					out[2]=max(out[2],x)
					out[3]=max(out[3],y)
			mask>>=1
		return tuple(out)

	@staticmethod
	def get_center(mask:int=-1,weighted:bool=False,hardware:LEDSignHardware|None=None) -> tuple[float,float]:
		"""
		Returns the center :python:`(cx, cy)` of all pixels selected by :python:`mask`. If no mask is given, the bounding box of all pixels is computed.

		If the :python:`weighted` flag is set, the center is weighted across all pixels locations. Otherwise, the center of the bounding box returned by :py:func:`get_bounding_box` is calculated.
		"""
		hardware=LEDSignSelector._check_hardware(hardware)
		if (not isinstance(mask,int)):
			raise TypeError(f"Expected 'int', got '{mask.__class__.__name__}'")
		if (not weighted):
			bbox=LEDSignSelector.get_bounding_box(mask,hardware)
			return ((bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2)
		cx=0.0
		cy=0.0
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
	def get_pixels(mask:int=-1,letter:int|None=None,hardware:LEDSignHardware|None=None) -> Iterator[tuple[float,float,int]]:
		"""
		Returns all pixel :python:`(x, y, mask)` tuples selected by :python:`mask`. If no mask is given, the bounding box of all pixels is computed.

		If the :python:`letter` index is given, only pixels from the given letter are processed.
		"""
		hardware=LEDSignSelector._check_hardware(hardware)
		if (not isinstance(mask,int)):
			raise TypeError(f"Expected 'int', got '{mask.__class__.__name__}'")
		if (letter is not None):
			mask&=LEDSignSelector.get_letter_mask(letter,hardware=hardware)
		m=1
		for i,xy in enumerate(hardware._pixels):
			if (xy is not None and (mask&m)):
				yield (xy[0],xy[1],m)
			m<<=1

	@staticmethod
	def get_letter_mask(index:int,hardware:LEDSignHardware|None=None) -> int:
		"""
		Returns the pixel mask corresponding to the letter selected by :python:`index`. Raises an :py:exc:`IndexError` if the index is out of bounds.
		"""
		hardware=LEDSignSelector._check_hardware(hardware)
		if (not isinstance(index,int)):
			raise TypeError(f"Expected 'int', got '{index.__class__.__name__}'")
		if (index<0):
			raise IndexError("Letter index out of range")
		for i in range(0,8):
			if (not hardware._raw_config[i]):
				continue
			if (not index):
				return ((1<<((i+1)*hardware._led_depth))-(1<<(i*hardware._led_depth)))&hardware._mask
			index-=1
		raise IndexError("Letter index out of range")

	@staticmethod
	def get_letter_masks(hardware:LEDSignHardware|None=None) -> Iterator[tuple[int,str,int]]:
		"""
		Returns all letter :python:`(index, character, mask)` tuples of the current hardware configuration.
		"""
		hardware=LEDSignSelector._check_hardware(hardware)
		j=0
		for i in range(0,8):
			if (not hardware._raw_config[i]):
				continue
			yield (j,chr(hardware._raw_config[i]),((1<<((i+1)*hardware._led_depth))-(1<<(i*hardware._led_depth)))&hardware._mask)
			j+=1

	@staticmethod
	def get_letter_count(hardware:LEDSignHardware|None=None) -> int:
		"""
		Returns the number of letters in the current hardware configuration.
		"""
		hardware=LEDSignSelector._check_hardware(hardware)
		out=0
		for i in range(0,8):
			if (hardware._raw_config[i]):
				out+=1
		return out

	@staticmethod
	def get_circle_mask(cx:int|float,cy:int|float,r:int|float,mask:int=-1,hardware:LEDSignHardware|None=None) -> int:
		"""
		Returns a mask selecting all pixels within the circle centered at :python:`(cx, cy)` with radius :python:`r`, selected by the provided :python:`mask`. If no mask is given, the all pixels are processed.
		"""
		hardware=LEDSignSelector._check_hardware(hardware)
		if (not isinstance(cx,int) and not isinstance(cx,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{cx.__class__.__name__}'")
		if (not isinstance(cy,int) and not isinstance(cy,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{cy.__class__.__name__}'")
		if (not isinstance(r,int) and not isinstance(r,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{r.__class__.__name__}'")
		if (r<0):
			raise ValueError(f"Radius must not be negative, got '{r}'")
		if (not isinstance(mask,int)):
			raise TypeError(f"Expected 'int', got '{mask.__class__.__name__}'")
		r*=r
		out=0
		for i,xy in enumerate(hardware._pixels):
			if (xy is not None and (mask&1) and (xy[0]-cx)**2+(xy[1]-cy)**2<=r):
				out|=1<<i
			mask>>=1
		return out
