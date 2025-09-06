import sys;sys.path.insert(0,"../..") # Use local ledsign module; note the file is renamed 'random_' to avoid circular imports of the built-in random module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector
import random



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	duration=0.2
	steps=10
	for x,y,mask in LEDSignSelector.get_pixels():
		at(0)
		for i in range(0,steps):
			kp(hsv(random.random()*360,1,1),mask)
			af(duration)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("random.led")
