from ledsign.device import LEDSign



devices=LEDSign.enumerate()
if (not devices):
	print("No devices found")
else:
	print("system devices:"+"".join(["\n  "+e for e in devices]))
	device=LEDSign.open(devices[0])
	print(f"current device:\n  path: {device.path} ({LEDSign.ACCESS_MODES[device.get_access_mode()]})\n  power supply: 5V {device.get_psu_current()*1000:.0f}mA ({device.get_psu_current()*5}W)\n  storage: {device.get_storage_size()} B\n  hardware: {device.get_hardware().get_string()}\n  firmware: {device.get_firmware()}\n  serial number: {device.get_serial_number()}\n  driver:\n    brightness: {device.get_driver_brightness()*100:.0f}%\n    paused: {str(device.is_driver_paused()).lower()}\n    temperature: {device.get_driver_temperature():.1f}*C\n    load: {device.get_driver_load():.1f}%\n    current: {device.get_driver_current_usage():.3f}A\n    program time: {device.get_driver_program_time():.3f}s / {device.get_driver_program_duration():.3f}s")
