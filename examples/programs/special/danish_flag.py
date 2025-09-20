import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	cx,cy=LEDSignSelector.get_center()
	cx*=0.4
	for x,y,mask in LEDSignSelector.get_pixels():
		if (min(abs(x-cx),abs(y-cy))<10):
			kp("#ffffff",mask)
		else:
			kp("#c8102e",mask)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("danish_flag.led")
