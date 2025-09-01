import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	for _,_,mask in LEDSignSelector.get_letter_masks():
		i=0
		j=0
		while (mask):
			if (mask&1):
				kp(hsv(j/LEDSignSelector.get_led_depth()*360,1,1),1<<i)
				j+=1
			i+=1
			mask>>=1
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("leds.led")
