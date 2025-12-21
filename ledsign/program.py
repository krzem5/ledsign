from collections.abc import Callable,Iterator
from ledsign.checksum import LEDSignCRC
from ledsign.keypoint_list import LEDSignKeypoint,LEDSignKeypointList
from ledsign.program_io import LEDSignCompiledProgram,LEDSignProgramParser
from ledsign.protocol import LEDSignProtocol
from ledsign.proxy import LEDSignProtocolError
from typing import Union
import ledsign.device
import os
import struct
import sys
import threading
import weakref



__all__=["LEDSignProgramError","LEDSignProgram","LEDSignProgramBuilder"]



class LEDSignProgramError(Exception):
	"""
	Raised whenever issues in a program's configuration are detected.
	"""



class LEDSignProgram(object):
	"""
	Contains information about a complete LED sign program compatible with :python:`device`. If the :python:`file_path` argument is given, the program is loaded from the specified file path.

	An instance of this class can be used as a function decorator to generate programs dynamically (see :py:class:`LEDSignProgramBuilder` or :py:func:`__call__` for details).
	"""

	error_output_file=sys.stderr

	__slots__=["_hardware","_duration","_keypoint_list","_load_parameters","_builder_ready","_has_error"]

	def __init__(self,device:"LEDSign",file_path:str|None=None) -> None:
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

	def __repr__(self) -> str:
		return f"<LEDSignProgram{('[unloaded]' if self._load_parameters is not None else '')} hardware={self._hardware.get_string()} duration={self._duration/60:.3f}s>"

	def __call__(self,func:Callable[[],None],args:tuple|list=(),kwargs:dict={},inject_commands:bool=True,bypass_errors:bool=False) -> "LEDSignProgram":
		"""
		Explicitly generates a program from the given function :python:`func(*args, **kwargs)`, and optionally bypasses error verification if the :python:`bypass_errors` flag is set. Explicit uses of this method are required when 'stitching' a program from multiple functions, or when it is necessary to pass arguments to the supplied function. An example use case might be the following:

		.. code-block:: python

			def mark_program_end(duration):
			    at(duration)
			    end()

			program = ledsign.LEDSignProgram(device)
			program(mark_program_end, args = (4.0,))
			@program # alternatively: program(program_body_fn)
			def program_body_fn():
			    kp("#ff0000")

		For advanced use cases, command alias injection can be disabled through the :python:`inject_commands` argument (see :py:class:`LEDSignProgramBuilder` for details about command shorthands).
		"""
		if (not callable(func)):
			raise TypeError(f"Expected 'function', got '{func.__class__.__name__}'")
		if (not isinstance(args,tuple) and not isinstance(args,list)):
			raise TypeError(f"Expected 'list' or 'tuple', got '{args.__class__.__name__}'")
		if (not isinstance(kwargs,dict)):
			raise TypeError(f"Expected 'dict', got '{kwargs.__class__.__name__}'")
		self._builder_ready=True
		builder=LEDSignProgramBuilder(self)
		self._builder_ready=False
		builder._change_lock(True)
		if (inject_commands):
			namespace=func.__globals__
			old_namespace={}
			for k,v in builder._get_function_list():
				if (k in namespace):
					old_namespace[k]=namespace[k]
				namespace[k]=v
		try:
			func(*args,**kwargs)
			if (bypass_errors):
				self._has_error=True
			else:
				self.verify()
		except Exception as e:
			self._has_error=True
			raise e
		finally:
			if (inject_commands):
				for k,_ in builder._get_function_list():
					if (k in old_namespace):
						namespace[k]=old_namespace[k]
					else:
						del namespace[k]
			builder._change_lock(False)
		return self

	def _add_raw_keypoint(self,rgb:int,end:int,duration:int,mask:int,frame:object) -> LEDSignKeypoint|None:
		mask&=self._hardware._mask
		if (not mask):
			return None
		out=LEDSignKeypoint(rgb,end,duration,mask,frame)
		self._keypoint_list.insert(out)
		return out

	def _load_from_file(self,file_path:str) -> None:
		size=os.stat(file_path).st_size
		if (size<8 or (size&3)):
			raise LEDSignProgramError("Invalid program")
		with open(file_path,"rb") as rf:
			ctrl,crc=struct.unpack("<II",rf.read(8))
			data=rf.read()
		if ((ctrl&0xff)%3 or size!=((ctrl>>8)<<2)+8 or crc!=LEDSignCRC(data).value):
			raise LEDSignProgramError("Invalid program")
		if (((self._hardware._pixel_count+7)>>3)!=(ctrl&0xff)//3):
			raise LEDSignProgramError("Program was compiled for different hardware")
		self._duration=(ctrl>>9)//max(ctrl&0xff,1)
		parser=LEDSignProgramParser(self,(ctrl&0xff)//3,True)
		parser.update(data)
		parser.terminate()

	def is_unloaded(self) -> bool:
		"""
		Returns :python:`True` if the program is unloaded (ie. not yet fetched from the device), and :python:`False` otherwise.
		"""
		return self._load_parameters is not None

	def get_duration(self) -> float:
		"""
		Returns the current duration of the program.
		"""
		return self._duration/60

	def compile(self,bypass_errors:bool=False) -> LEDSignCompiledProgram:
		"""
		Compiles the program and returns a :py:class:`LEDSignCompiledProgram` object, and optionally bypasses error verification if the :python:`bypass_errors` flag is set. Raises :py:exc:`LEDSignProgramError` if the program contains unresolved errors.
		"""
		self.load()
		if (self._has_error and not bypass_errors):
			raise LEDSignProgramError("Unresolved program errors")
		return LEDSignCompiledProgram(self,False)

	def save(self,file_path:str,bypass_errors:bool=False) -> None:
		"""
		Writes the program to a file pointed to by the :python:`file_path`. Optionally bypasses error verification (if the :python:`bypass_errors` flag is set), or raises :py:exc:`LEDSignProgramError` if the program contains unresolved errors.
		"""
		if (not isinstance(file_path,str)):
			raise TypeError(f"Expected 'str', got '{file_path.__class__.__name__}'")
		self.load()
		if (self._has_error and not bypass_errors):
			raise LEDSignProgramError("Unresolved program errors")
		LEDSignCompiledProgram(self,True)._save_to_file(file_path)

	def load(self) -> None:
		"""
		Explicitly loads an unloaded device program. Does nothing if the program was already downloaded, or if the program was not sourced from a :py:class:`LEDSign` device.

		Raises :py:exc:`LEDSignProtocolError` or :py:exc:`LEDSignProgramError` if the device was closed or modified before this method was called.
		"""
		if (self._load_parameters is None):
			return
		load_parameters=self._load_parameters
		self._load_parameters=None
		device=load_parameters[0]()
		if (device is None or device._path is None):
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
			self._keypoint_list.clear()
			self._has_error=True
			raise LEDSignProgramError("Mismatched program checksum")
		parser.terminate()

	def get_keypoints(self,mask:int=-1) -> Iterator[LEDSignKeypoint]:
		"""
		Iterates over all keypoints containing any pixels selected by :python:`mask`. If no mask is given, all keypoints are iterated over.
		"""
		if (not isinstance(mask,int)):
			raise TypeError(f"Expected 'int', got '{mask.__class__.__name__}'")
		self.load()
		return self._keypoint_list.iterate(mask)

	def verify(self) -> bool:
		"""
		Verifies the program, and reports any encountered errors. Returns :python:`True` if no errors have been found, and :python:`False` otherwise.
		"""
		self.load()
		self._has_error=False
		kp=self._keypoint_list.lookup_increasing(0,-1)
		while (kp is not None):
			start=kp.end-kp.duration
			if (start<0):
				print(f"Keypoint overlap: ({-start/60:.3f}s)\n  <timeline_start>\n  {kp._frame}",file=LEDSignProgram.error_output_file)
				self._has_error=True
			entry=self._keypoint_list.lookup_decreasing(kp._key-1,kp.mask)
			while (entry is not None and entry.end>start):
				print(f"Keypoint overlap: ({(entry.end-start)/60:.3f}s)\n  {entry._frame}\n  {kp._frame}",file=LEDSignProgram.error_output_file)
				self._has_error=True
				entry=self._keypoint_list.lookup_decreasing(entry._key-1,kp.mask)
			kp=self._keypoint_list.lookup_increasing(kp._key+1,-1)
		return not self._has_error

	@staticmethod
	def _create_unloaded_from_device(device:"LEDSign",ctrl:int,crc:int) -> "LEDSignProgram":
		out=LEDSignProgram(device)
		out._duration=(ctrl>>9)//max(ctrl&0xff,1)
		if (ctrl>>8):
			out._load_parameters=(weakref.ref(device),ctrl,crc)
		return out



class LEDSignProgramBuilder(object):
	"""
	The :py:class:`LEDSignProgramBuilder` class maintains context needed for dynamic program generation. It cannot be created directly; instead it is globally available via :py:func:`LEDSignProgramBuilder.instance` within the stack frames of a decorated :py:class:`LEDSignProgram` function (or function called passed to :py:func:`LEDSignProgram.__call__`).

	For convenience reasons, all program builder commands are made available in the program function's global scope, with shorthand aliases for longer ones. The following commands and shortcuts are injected into the global scope:

	+--------------------+-------------+-------------------------------+
	| Command            | Shortcut    | Builder method                |
	+====================+=============+===============================+
	| :func:`after`      | :func:`af`  | :py:func:`command_after`      |
	+--------------------+-------------+-------------------------------+
	| :func:`at`         | ---         | :py:func:`command_at`         |
	+--------------------+-------------+-------------------------------+
	| :func:`cross_fade` | :func:`cf`  | :py:func:`command_cross_fade` |
	+--------------------+-------------+-------------------------------+
	| :func:`delta_time` | :func:`dt`  | :py:func:`command_delta_time` |
	+--------------------+-------------+-------------------------------+
	| :func:`end`        | ---         | :py:func:`command_end`        |
	+--------------------+-------------+-------------------------------+
	| :func:`hsv`        | ---         | :py:func:`command_hsv`        |
	+--------------------+-------------+-------------------------------+
	| :func:`hardware`   | :func:`hw`  | :py:func:`command_hardware`   |
	+--------------------+-------------+-------------------------------+
	| :func:`keypoint`   | :func:`kp`  | :py:func:`command_keypoint`   |
	+--------------------+-------------+-------------------------------+
	| :func:`rgb`        | ---         | :py:func:`command_rgb`        |
	+--------------------+-------------+-------------------------------+
	| :func:`time`       | :func:`tm`  | :py:func:`command_time`       |
	+--------------------+-------------+-------------------------------+

	The following example illustrates the three different ways of accessing the :python:`keypoint` command:

	.. code-block:: python

		@ledsign.LEDSignProgram(device)
		def program():
		    at(0)
		    keypoint("#ff0000") # <-- alias of the 'keypoint' command
		    after(1)
		    kp("#00ff00") # <-- shortcut for the 'keypoint' command
		    after(1)
		    builder=LEDSignProgramBuilder.instance()
		    builder.command_keypoint("#0000ff") # <-- underlying 'keypoint' command
		    after(1)
		    end()

	.. note::

		Due to limitations of the internal implementation, these shortcuts can only be accessed by code located within the same file (ie. sharing the same global scope) as the executed program generation function. In other contexts (such as in functions where local closures re-define the command aliases), all commands can be accessed through the current program builder instance, ex. :python:`LEDSignProgramBuilder.instance().command_end()`.
	"""

	COMMANDS={
		"af": "after",
		"at": "at",
		"cf": "cross_fade",
		"dt": "delta_time",
		"end": "end",
		"hsv": "hsv",
		"hw": "hardware",
		"kp": "keypoint",
		"rgb": "rgb",
		"tm": "time"
	}

	_global_lock=threading.Lock()
	_current_instance=None

	__slots__=["program","time"]

	def __init__(self,program:LEDSignProgram) -> None:
		if (not isinstance(program,LEDSignProgram) or not program._builder_ready):
			raise TypeError("Direct initialization of LEDSignProgramBuilder is not supported")
		self.program=program
		self.time=1

	def _change_lock(self,enable:bool) -> None:
		if (enable):
			LEDSignProgramBuilder._global_lock.acquire()
			LEDSignProgramBuilder._current_instance=self
		else:
			LEDSignProgramBuilder._current_instance=None
			LEDSignProgramBuilder._global_lock.release()

	def _get_function_list(self) -> Iterator[tuple[str,Callable]]:
		for k,v in LEDSignProgramBuilder.COMMANDS.items():
			func=getattr(self,"command_"+v)
			yield (k,func)
			if (k!=v):
				yield (v,func)

	def _parse_color(self,rgb:int|str) -> int:
		if (isinstance(rgb,int)):
			rgb&=0xffffff
		elif (isinstance(rgb,str) and len(rgb)==7 and rgb[0]=="#"):
			rgb=int(rgb[1:7],16)
		else:
			raise TypeError(f"Expected 'int' or 'hex-color', got '{rgb.__class__.__name__}'")
		return rgb

	def command_at(self,time:int|float) -> float:
		"""
		Sets the current timestamp to :python:`time` (in seconds), and returns this new value. Negative values are clamped to :python:`0.0`.
		"""
		if (not isinstance(time,int) and not isinstance(time,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{time.__class__.__name__}'")
		self.time=max(round(time*60),1)
		return self.time/60

	def command_after(self,delta_time:int|float) -> float:
		"""
		Advances the current timestamp by :python:`delta_time` (in seconds), and returns its new value. Negative values move back the time, clamping to :python:`0.0` if the resulting timestamp becomes negative.
		"""
		if (not isinstance(delta_time,int) and not isinstance(delta_time,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{delta_time.__class__.__name__}'")
		self.time=max(self.time+round(delta_time*60),1)
		return self.time/60

	def command_delta_time(self) -> float:
		"""
		Returns the interval between consecutive program frames, in seconds.
		"""
		return 1/60

	def command_time(self) -> float:
		"""
		Returns the current timestamp, in seconds.
		"""
		return self.time/60

	def command_hardware(self) -> "LEDSignHardware":
		"""
		Returns the :py:class:`LEDSignHardware` object associated with the current program. Can be used as an explicit argument for functions from the :py:class:`LEDSignSelector` class (although these functions will call this method internally if no explicit hardware object is supplied to them).
		"""
		return self.program._hardware

	def command_keypoint(self,rgb:int|str,mask:int=-1,duration:int|float|None=None,time:int|float|None=None) -> LEDSignKeypoint:
		"""
		Creates an :python:`rgb`-colored keypoint. Both integer (:code:`0xrrggbb`) and HTML (:python:`"#rrggbb"`) colors are supported. For other color formats, convert their respective arguments using :py:func:`command_rgb` or :py:func:`command_hsv`.

		If the :python:`mask` argument is given, only pixels selected by the provided mask will have this keypoint applied to them.

		The duration of the animation is specified by the :python:`duration` argument (in seconds). If left undefined or negative, the animation will be instant.

		If the :python:`time` argument is omitted, the keypoint will terminate at the currently selected timestamp. Otherwise, the keypoint will end at timestamp :python:`time`, given in seconds.

		.. warning::

			During program verification, each keypoint is checked to prevent invalid configurations, usually resulting from bugs in generator code. Two types of invalid keypoint configurations are: (1) negative start time, and (2) ambiguous ordering.

			The first error is reported with a keypoint's start time (ie. its end time minus its duration) predates the start of the program (timestamp :python:`0.0`). The compiler is not be able generate the full extent of the animation, and thus the end result is undefined.

			The second error occurs when at any point more than one keypoint attempts to apply an animation to the same pixel. Due to undefined compilation ordering, the produced results may not be consistent across compilations.

			However, for increased performance, these error-checking functions can be postponed or disabled altogether by setting the :python:`bypass_errors` flag in relevant :py:class:`LEDSignProgram` functions.
		"""
		rgb=self._parse_color(rgb)
		if (not isinstance(mask,int)):
			raise TypeError(f"Expected 'int', got '{mask.__class__.__name__}'")
		if (duration is None):
			duration=1
		elif (isinstance(duration,int) or isinstance(duration,float)):
			duration=max(round(duration*60),1)
		else:
			raise TypeError(f"Expected 'int' or 'float', got '{duration.__class__.__name__}'")
		if (time is None):
			time=self.time
		elif (isinstance(time,int) or isinstance(time,float)):
			time=max(round(time*60),1)
		else:
			raise TypeError(f"Expected 'int' or 'float', got '{time.__class__.__name__}'")
		return self.program._add_raw_keypoint(rgb,time,duration,mask,(sys._getframe(1) if hasattr(sys,"_getframe") else None))

	def command_end(self) -> None:
		"""
		Places the program end marker at the current timestamp. All animations after this timestamp will not be compiled. Can be used multiple times to adjust the length of the program.
		"""
		self.program._duration=self.time

	def command_rgb(self,r:int|float,g:int|float,b:int|float) -> int:
		"""
		Converts the given :python:`(r, g, b)` tuple (each element is clamped between :python:`0.0` and :python:`1.0`) into a packed 24-bit integer color. Can be used to pack individual :python:`int` or :python:`float` color channels for use with the :py:func:`command_keypoint` function.
		"""
		if (not isinstance(r,int) and not isinstance(r,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{r.__class__.__name__}'")
		if (not isinstance(g,int) and not isinstance(g,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{g.__class__.__name__}'")
		if (not isinstance(b,int) and not isinstance(b,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{b.__class__.__name__}'")
		r=min(max(round(r*255),0),255)
		g=min(max(round(g*255),0),255)
		b=min(max(round(b*255),0),255)
		return (r<<16)+(g<<8)+b

	def command_hsv(self,h:int|float,s:int|float,v:int|float) -> int:
		"""
		Converts the given :python:`(h, s, v)` tuple (each element is clamped between :python:`0.0` and :python:`1.0`) into a packed 24-bit integer color. Can be used to generate HSV colors for use with the :py:func:`command_keypoint` function.
		"""
		if (not isinstance(h,int) and not isinstance(h,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{h.__class__.__name__}'")
		if (not isinstance(s,int) and not isinstance(s,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{s.__class__.__name__}'")
		if (not isinstance(v,int) and not isinstance(v,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{v.__class__.__name__}'")
		h=(h%1.0)*6
		s=min(max(s,0),1)
		v=min(max(round(v*255),0),255)
		if (s==0):
			return v*0x010101
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

	def command_cross_fade(self,src:int|str,dst:int|str,t:int|float) -> int:
		"""
		Computes the cross-fade (linearly interpolated) between colors :python:`src` and :python:`dst`, at time :python:`t` (normalized between :python:`0.0` and :python:`1.0`). Both integer (:code:`0xrrggbb`) and HTML (:python:`"#rrggbb"`) colors are supported. For other color formats, convert their respective arguments using :py:func:`command_rgb` or :py:func:`command_hsv`.
		"""
		src=self._parse_color(src)
		dst=self._parse_color(dst)
		if (not isinstance(t,int) and not isinstance(t,float)):
			raise TypeError(f"Expected 'int' or 'float', got '{t.__class__.__name__}'")
		t=min(max(t,0),1)
		cr=min(max(round(((src>>16)&0xff)+t*(((dst>>16)&0xff)-((src>>16)&0xff))),0),255)
		cg=min(max(round(((src>>8)&0xff)+t*(((dst>>8)&0xff)-((src>>8)&0xff))),0),255)
		cb=min(max(round((src&0xff)+t*((dst&0xff)-(src&0xff))),0),255)
		return (cr<<16)+(cg<<8)+cb

	@staticmethod
	def instance() -> Union["LEDSignProgramBuilder",None]:
		"""
		Returns the current active instance of :py:class:`LEDSignProgramBuilder`, or :python:`None` if none are active.
		"""
		return LEDSignProgramBuilder._current_instance
