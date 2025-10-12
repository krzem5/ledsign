import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	colors=[0xdc8add,0xe2227c,0xeb16f0,0x914da9]
	duration=4
	for x,y,mask in LEDSignSelector.get_pixels():
		at(0)
		while (tm()<=duration):
			v=(x-y)/50-tm()/duration*len(colors)+100
			kp(cf(colors[int(v)%len(colors)],colors[(int(v)+1)%len(colors)],v%1),mask)
			af(dt())
	at(duration)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("pink_fade.led")
