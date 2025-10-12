import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	columns={}
	for x,y,_ in LEDSignSelector.get_pixels():
		if (x not in columns):
			columns[x]=1
		else:
			columns[x]+=1
	cx=sorted(columns.items(),key=lambda e:(-e[1],e[0]))[1][0]
	cy=LEDSignSelector.get_center()[1]
	for x,y,mask in LEDSignSelector.get_pixels():
		kp(("#ffffff" if x==cx or abs(y-cy)<10 else "#c8102e"),mask)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("danish_flag.led")
