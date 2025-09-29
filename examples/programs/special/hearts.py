import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector
import random



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	bbox=LEDSignSelector.get_bounding_box()
	duration=2
	circle_lifetime=1.0
	circle_delay_interval=(0.8,1.1)
	circles=[]
	last_circle_time=0
	while (True):
		last_circle_time+=circle_delay_interval[0]+random.random()*(circle_delay_interval[1]-circle_delay_interval[0])
		circles.insert(0,(
			bbox[0]+random.random()*(bbox[2]-bbox[0]),
			bbox[1]+random.random()*(bbox[3]-bbox[1]),
			(bbox[2]-bbox[0])*(random.random()/2+1/8),
			last_circle_time
		))
		if (len(circles)>10):
			break
	while (tm()<=duration):
		mask=-1
		for x,y,r,t in circles:
			u=((tm()-t)%duration)/circle_lifetime
			if (u>=1):
				continue
			circle_mask=LEDSignSelector.get_circle_mask(x,y,r*u,mask)
			kp(hsv(t/duration*360,1,(1-u)**2),circle_mask)
			print(f"{hsv(t/duration*360,1,(1-u)**2):06x}",circle_mask)
			mask&=~circle_mask
		kp("#000000",mask)
		af(dt())
	at(duration)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("hearts.led")
