import sys;sys.path.insert(0,"../../..") # Use local ledsign module

from ledsign import LEDSign,LEDSignProgram



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	kp("#ffffff",-1)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("max_current.led")
