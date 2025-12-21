from ledsign.device import LEDSign
from ledsign.program import LEDSignProgram
from ledsign.proxy import LEDSignProxyServer
import optparse



_device_list_cache=[]
def _get_device_list() -> list[str]:
	if (not _device_list_cache):
		_device_list_cache.extend(LEDSign.enumerate())
	return _device_list_cache



def _upload_callback(progress:float,is_upload:bool) -> None:
	print(f"{('Upload' if is_upload else 'Clear')} progress: {progress*100:.0f}%")



def main() -> None:
	parser=optparse.OptionParser(prog="ledsign",version="%prog v0.8.0")
	parser.add_option("-d","--device",metavar="DEVICE_PATH|DEVICE_INDEX",dest="device_path",help="open device at DEVICE_PATH, or the device at index DEVICE_INDEX (leave empty to use default device path)")
	parser.add_option("-e","--enumerate",action="store_true",dest="enumerate",help="enumerate all available devices")
	parser.add_option("-x","--enumerate-only",action="store_true",dest="enumerate_only",help="enumerate all available devices and exit (implies --enumerate)")
	parser.add_option("-i","--print-info",action="store_true",dest="print_info",help="print device hardware information")
	parser.add_option("-c","--print-config",action="store_true",dest="print_config",help="print device configuration")
	parser.add_option("-p","--print-driver",action="store_true",dest="print_driver",help="print driver stats")
	parser.add_option("-s","--save",metavar="PROGRAM",dest="save_program",help="save current program into PROGRAM")
	parser.add_option("-u","--upload",metavar="PROGRAM",dest="upload_program",help="upload file PROGRAM to the device (requires read-write mode)")
	parser.add_option("-z","--start-proxy-server",action="store_true",help="start a proxy server (required to communicate with the device)")
	options,args=parser.parse_args()
	if (options.start_proxy_server):
		LEDSignProxyServer()
		input(f"Proxy server running on port {LEDSignProxyServer.PROXY_PORT}, hit 'Enter' to stop\n")
		return
	device_path=None
	if (not options.enumerate_only):
		if (options.device_path is None):
			if (not _get_device_list()):
				print("No devices found")
				return
			device_path=_get_device_list()[0]
		elif (options.device_path.isnumeric()):
			device_index=int(options.device_path)
			if (device_index>=len(_get_device_list())):
				parser.error("option -d: device index out of range")
				return
			device_path=_get_device_list()[device_index]
		else:
			device_path=options.device_path
	if (options.enumerate or options.enumerate_only):
		devices=LEDSign.enumerate()
		print("system devices:"+"".join([f"\n  {e}" for e in devices]))
		if (options.enumerate_only):
			return
	if (not options.print_info and not options.print_config and not options.print_driver and not options.save_program and not options.upload_program):
		options.print_info=True
		options.print_config=True
		options.print_driver=True
	device=LEDSign.open(device_path)
	try:
		if (options.print_info):
			print(f"device:\n  path: {device.get_path()}\n  storage: {device.get_storage_size()} B\n  hardware: {device.get_hardware().get_string()} ({device.get_hardware().get_user_string()})\n  firmware: {device.get_firmware()}\n  serial number: {device.get_serial_number_str()}")
		if (options.print_config):
			print(f"config:\n  access mode: {device.get_access_mode_str()}\n  power supply: 5V {device.get_psu_current()*1000:.0f}mA ({device.get_psu_current()*5}W)")
		if (options.print_driver):
			print(f"driver:\n  brightness: {device.get_driver_brightness()*100:.0f}%\n  paused: {str(device.is_driver_paused()).lower()}\n  temperature: {device.get_driver_temperature():.1f}*C\n  load: {device.get_driver_load():.1f}%\n  current: {device.get_driver_current_usage()*1000:.0f}mA\n  program time: {device.get_driver_program_time():.3f}s / {device.get_program().get_duration():.3f}s")
		if (options.save_program):
			device.get_program().save(options.save_program)
		if (options.upload_program):
			device.upload_program(LEDSignProgram(device,options.upload_program).compile(),_upload_callback)
	finally:
		device.close()



if (__name__=="__main__"):
	main()
