import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram



strobe_pattern="white"
strobe_pattern="rainbow"
strobe_pattern="red-blue"



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	kp("#ffffff",-1)
	af(dt())
	kp("#000000",-1)
	af(dt()*3)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("white.led")
