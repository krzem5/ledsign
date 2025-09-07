import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	kp("#ff0000",-1)
	af(dt()*4)
	kp("#000000",-1)
	af(dt()*6)
	kp("#0000aa",-1)
	af(dt()*4)
	kp("#000000",-1)
	af(dt()*5)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("red_blue.led")
