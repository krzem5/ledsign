import sys;sys.path.insert(0,"..") # Use local ledsign module

from ledsign import LEDSign



device=LEDSign.open()
program=device.get_program()
print(f"Before load:{program}")
program.load()
print(f"After load: {program}")
program.save("program.led")
