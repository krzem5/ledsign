import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector
import math



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	cx,cy=LEDSignSelector.get_center()
	cy=0
	duration=8
	for x,y,mask in LEDSignSelector.get_pixels():
		offset=math.hypot(x-cx,y-cy)/200
		at(0)
		while (tm()<=duration):
			kp(hsv(1+(math.cos(2*math.pi*(tm()/duration-offset))*0.5-0.5)*0.2,1,1),mask)
			af(dt())
	at(duration)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("pink_fade.led")
