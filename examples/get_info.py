import sys;sys.path.insert(0,"..") # Use local ledsign module
from ledsign import LEDSign



devices=LEDSign.enumerate()
if (not devices):
	print("No devices found")
else:
	for i,path in enumerate(devices):
		device=LEDSign.open(path)
		print(f"device {i}:\n  device:\n    path: {device.get_path()}\n    storage: {device.get_storage_size()} B\n    hardware: {device.get_hardware().get_string()} ({device.get_hardware().get_user_string()})\n    firmware: {device.get_firmware()}\n    serial number: {device.get_serial_number_str()}\n  config:\n    access mode: {device.get_access_mode_str()}\n    power supply: 5V {device.get_psu_current()*1000:.0f}mA ({device.get_psu_current()*5}W)\n  driver:\n    brightness: {device.get_driver_brightness()*100:.0f}%\n    paused: {str(device.is_driver_paused()).lower()}\n    temperature: {device.get_driver_temperature():.1f}*C\n    load: {device.get_driver_load():.1f}%\n    current: {device.get_driver_current_usage()*1000:.0f}mA\n    program time: {device.get_driver_program_time():.3f}s / {device.get_program().get_duration():.3f}s")
		device.close()
