from ledsign.device import LEDSign
import optparse



_device_list_cache=[]
def _get_device_list():
	if (not _device_list_cache):
		_device_list_cache.extend(LEDSign.enumerate())
	return _device_list_cache



def main():
	parser=optparse.OptionParser(prog="ledsign",version="%prog v0.4.0")
	parser.add_option("-p","--path",metavar="DEVICE_PATH",dest="device_path",help="open device at DEVICE_PATH (leave empty to use default device path)")
	parser.add_option("-e","--enumerate",action="store_true",dest="enumerate",help="enumerate all available devices")
	parser.add_option("-i","--print-info",action="store_true",dest="print_info",help="print device information")
	parser.add_option("-s","--print-settings",action="store_true",dest="print_settings",help="print device settings")
	parser.add_option("-d","--print-driver",action="store_true",dest="print_driver",help="print driver stats")
	options,args=parser.parse_args()
	device_path=None
	if (options.device_path is None):
		device_path=_get_device_list()[0]
	elif (options.device_path.isnumeric()):
		device_index=int(options.device_path)
		if (device_index>=len(_get_device_list())):
			parser.error("option -d: device index out of range")
			return
		device_path=_get_device_list()[device_index]
	else:
		device_path=options.device_path
	if (options.enumerate):
		devices=LEDSign.enumerate()
		print("system devices:"+"".join([f"\n  {e}" for e in devices]))
	if (not options.print_info and not options.print_settings and not options.print_driver):
		options.print_info=True
		options.print_settings=True
		options.print_driver=True
	device=LEDSign.open(device_path)
	if (options.print_info):
		print(f"device:\n  path: {device.path}\n  storage: {device.get_storage_size()} B\n  hardware: {device.get_hardware().get_string()}\n  firmware: {device.get_firmware()}\n  serial number: {device.get_serial_number()}")
	if (options.print_settings):
		print(f"settings:\n  access mode: {LEDSign.ACCESS_MODES[device.get_access_mode()]}\n  power supply: 5V {device.get_psu_current()*1000:.0f}mA ({device.get_psu_current()*5}W)")
	if (options.print_driver):
		print(f"driver:\n  brightness: {device.get_driver_brightness()*100:.0f}%\n  paused: {str(device.is_driver_paused()).lower()}\n  temperature: {device.get_driver_temperature():.1f}*C\n  load: {device.get_driver_load():.1f}%\n  current: {device.get_driver_current_usage()*1000:.0f}mA\n  program time: {device.get_driver_program_time():.3f}s / {device.get_driver_program_duration():.3f}s")
	device.close()



if (__name__=="__main__"):
	main()
