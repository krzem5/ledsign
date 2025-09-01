import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	bbox=LEDSignSelector.get_bounding_box()
	for x,y,mask in LEDSignSelector.get_pixels():
		kp(rgb((x-bbox[0])/(bbox[2]-bbox[0])*255,(y-bbox[1])/(bbox[3]-bbox[1])*255,128),mask)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("pixels.led")
