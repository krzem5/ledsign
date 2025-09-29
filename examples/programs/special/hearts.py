import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector
import math



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	cx,cy=LEDSignSelector.get_center(LEDSignSelector.get_letter_mask(0))
	for x,y,mask in LEDSignSelector.get_pixels():
		dx=x-cx
		dy=cy-y
		at(0)
		for t in range(0,60):
			r=t/60*cx*2+1
			ddx=dx/r
			ddy=dy/r
			if ((ddx*ddx+ddy*ddy-1)**3<ddx*ddx*ddy**3):
				kp("#ff0000",mask)
			else:
				r+=10
				ddx=dx/r
				ddy=dy/r
				if ((ddx*ddx+ddy*ddy-1)**3<ddx*ddx*ddy**3):
					kp("#800000",mask)
				else:
					r+=10
					ddx=dx/r
					ddy=dy/r
					if ((ddx*ddx+ddy*ddy-1)**3<ddx*ddx*ddy**3):
						kp("#400000",mask)
			af(1/60)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("hearts.led")
