import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector
import math



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	lines=[]
	dx=0
	dy=0
	px=0
	py=0
	expected_angle=None
	for x,y,mask in LEDSignSelector.get_pixels():
		if (not lines or (x-px-dx)**2+(y-py-dy)**2>(50 if expected_angle is None else 45) or (expected_angle is not None and abs((x-px)*dy+(y-py)*dx-expected_angle)>5)):
			lines.append(mask)
			dx=0
			dy=0
			px=x
			py=y
			expected_angle=None
		else:
			if (abs(dx)+abs(dy)>1):
				expected_angle=(x-px)*dy+(y-py)*dx
			lines[-1]|=mask
			dx=x-px
			dy=y-py
			px=x
			py=y
	for i,mask in enumerate(lines):
		kp(hsv(i/len(lines),1,1),mask)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("lines.led")
