import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	for color in ["#ff0000","#ffff00","#00ff00","#00ffff","#0000ff","#ff00ff"]:
		kp(color)
		af(dt()*5)
		kp("#000000")
		af(dt()*8)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("rainbow.led")
