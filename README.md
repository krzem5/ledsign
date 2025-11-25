# LED Sign

This `ledsign` module allows the direct control and programming of the LED Sign series of devices using Python 3, or through a dedicated CLI interface. This module however does **not** allow for hardware-level configuration of the device, as any such modifications must be done through the dedicated UI interface.

The documentation is hosted on ReadTheDocs, accessible through this [link](https://ledsign.readthedocs.io/en/latest/).

## Installation

The `ledsign` is available for easy download via PyPI. It can be installed with `pip`:

```
$ pip install ledsign
```


Alternatively, development versions can be installed directly from the [GitHub repository](https://github.com/krzem5/ledsign):

```
$ git clone https://github.com/krzem5/ledsign
$ cd ledsign
$ pip install -e .
```

## CLI Interface

Outside of the programmatic interface outlined in the Documentation, the `ledsign` module also features a command-line interface, accessible through the Python executable:

```
$ python -m ledsign -h
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
