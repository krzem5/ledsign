import sys;sys.path.insert(0,"../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	d=0.5
	kp("#ff0000",-1)
	af(d)
	kp("#ffff00",-1)
	af(d)
	kp("#00ff00",-1)
	af(d)
	kp("#00ffff",-1)
	af(d)
	kp("#0000ff",-1)
	af(d)
	kp("#ff00ff",-1)
	af(d)
	kp("#ff0000",-1)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("color_strobe.led")
