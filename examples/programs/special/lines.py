import sys;sys.path.insert(0,"../../..") # Use local ledsign module
from ledsign import LEDSign,LEDSignProgram,LEDSignSelector
import math
import random



device=LEDSign.open()



@LEDSignProgram(device)
def program():
	colors=["#ff0000","#ff8800","#ffff00","#00ff00","#2266ff","#bb00ff"]
	blink_count=8
	blink_max_duration=0.2
	duration=60
	lines=[]
	dx=0
	dy=0
	px=0
	py=0
	expected_angle=None
	for x,y,mask in LEDSignSelector.get_pixels():
		if (not lines or (x-px-dx)**2+(y-py-dy)**2>(50 if expected_angle is None else 45) or (expected_angle is not None and abs((x-px)*dy+(y-py)*dx-expected_angle)>5)):
			lines.append(mask)
			dx=0
			dy=0
			px=x
			py=y
			expected_angle=None
		else:
			if (abs(dx)+abs(dy)>1):
				expected_angle=(x-px)*dy+(y-py)*dx
			lines[-1]|=mask
			dx=x-px
			dy=y-py
			px=x
			py=y
	color_weights=[(LEDSignSelector.get_mask().bit_count()+len(colors)-1)//len(colors) for _ in range(0,len(colors))]
	prev_color_index=0
	blinking_lines=random.sample(range(0,len(lines)),blink_count)
	for i,mask in enumerate(lines):
		weight_sum=sum(color_weights)-color_weights[prev_color_index]-1
		if (not weight_sum):
			prev_color_index=-1
			weight_sum+=color_weights[prev_color_index]
		j=random.randint(0,weight_sum)
		for k in range(0,len(colors)):
			if (k==prev_color_index):
				continue
			j-=color_weights[k]
			if (j<0):
				break
		prev_color_index=k
		color_weights[prev_color_index]=max(color_weights[prev_color_index]-mask.bit_count(),0)
		at(0)
		kp(colors[prev_color_index],mask)
		if (i in blinking_lines):
			at(random.random()*(duration-2*blink_max_duration)+blink_max_duration)
			kp("#000000",mask)
			af((random.random()+1)/2*blink_max_duration)
			kp(colors[prev_color_index],mask)
	at(duration)
	end()



if (device.get_access_mode()==LEDSign.ACCESS_MODE_READ_WRITE):
	device.upload_program(program.compile())
else:
	program.save("lines.led")
