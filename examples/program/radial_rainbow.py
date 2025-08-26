import sys;sys.path.insert(0,"../..") # Use local ledsign module

from ledsign import LEDSign,LEDSignProgram,LEDSignSelector
import math



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	cx,cy=LEDSignSelector.get_center()
	duration=8
	X=0
	for x,y,mask in LEDSignSelector.get_pixels():
		offset=math.hypot(x-cx,y-cy)/300
		at(0)
		while (tm()<=duration):
			kp(hsv((tm()/duration-offset)*360,1,1),mask)
			af(dt())
			X+=1
	at(duration)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("program.led")
