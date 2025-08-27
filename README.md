# LED Sign

## Installation

`ledsign` is available for download via PyPI. It can be install with `pip`:

```bash
$ pip install ledsign
```

## Usage

The package also features a command-line interface, with options for common operations:
```bash
$ python3 -m ledsign
Usage: ledsign [options]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -d DEVICE_PATH|DEVICE_INDEX, --device=DEVICE_PATH|DEVICE_INDEX
                        open device at DEVICE_PATH, or the device at index
                        DEVICE_INDEX (leave empty to use default device path)
  -e, --enumerate       enumerate all available devices
  -x, --enumerate-only  enumerate all available devices and exit (implies
                        --enumerate)
  -i, --print-info      print device hardware information
  -c, --print-config    print device configuration
  -p, --print-driver    print driver stats
  -s PROGRAM, --save=PROGRAM
                        save current program into PROGRAM
  -u PROGRAM, --upload=PROGRAM
                        upload file PROGRAM to the device (requires read-write
                        mode)
```
