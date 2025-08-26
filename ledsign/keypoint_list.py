__all__=["LEDSignKeypoint","LEDSignKeypointList"]



class LEDSignKeypoint(object):
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
		return f"<LEDSignKeypoint color=#{self.rgb:06x} duration={self.duration/60:.3f}s end={self.end/60:.3f}s mask={self.mask:x}>"



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
