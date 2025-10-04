import sys;sys.path.insert(0,"../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	duration=2
	fade=0.4
	bbox=LEDSignSelector.get_bounding_box()
	height=bbox[3]-bbox[1]
	fade_height=height*fade
	hue_map={}
	for i,_,mask in LEDSignSelector.get_letter_masks():
		hue_map[mask]=i/LEDSignSelector.get_letter_count()
	for x,y,mask in LEDSignSelector.get_pixels():
		for letter_mask in hue_map:
			if (letter_mask&mask):
				hue=hue_map[letter_mask]
				break
		at(0)
		for i in range(0,round(duration/dt())):
			bar_y=i*dt()/duration*(height+2*fade_height)+bbox[1]-fade_height
			s=min(abs(y-bar_y)/fade_height,1)
			kp(hsv(hue,s,1),mask)
			af(dt())
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("vertical_fade.led")
