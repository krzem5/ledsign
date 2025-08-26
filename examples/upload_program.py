import sys;sys.path.insert(0,"..") # Use local ledsign module

from ledsign import LEDSign,LEDSignProgram



device=LEDSign.open()
program=LEDSignProgram(device,"program.led")
device.upload_program(program.compile())
