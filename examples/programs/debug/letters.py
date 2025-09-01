import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	for i,_,mask in LEDSignSelector.get_letter_masks():
		kp(hsv(i/LEDSignSelector.get_letter_count()*360,1,1),mask)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("letters.led")
