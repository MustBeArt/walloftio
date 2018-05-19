# Wall of Trans-Ionospheric at Dayton Hamvention 2018

Brought to you by Abraxas3D and Skunkwrx.

Based on the [Wall of Bender](https://github.com/MustBeArt/wallofbender)
and the [Wall of JoCo](https://github.com/MustBeArt/wallofjoco).

## Introduction

The **Wall of Trans-Ionospheric** is a logger and display board for the 
Trans-Ionospheric badge. The badge has a Bluetooth Low Energy (BLE) 
radio. Each badge is constantly transmitting its unique ID, player 
name, and other game info in BLE advertisement format. The Wall listens 
for these advertisements, logs them all to a file, and displays them in 
a friendly format for the amusement and edification of passers-by.

Three windows are displayed. A smaller window displays just the names and
unique IDs of each and every badge advertisement received, in real time,
even if they go by too fast to read. A bigger window displays the same
information plus a time-since-last-heard indication, and scrolls
the entire stored list, after removing duplicates based on the BLE
advertising address transmitted. In between, another scrolled
window shows just the names received, regardless of which badge sent them.

## Hardware

We deployed the Wall of Trans-Ionospheric on a
[Raspberry Pi Zero W](https://www.raspberrypi.org/products/raspberry-pi-zero-w/).

The Raspberry Pi Zero W does not have an on-board realtime clock, so we 
added an [Adafruit PiRTC Real Time Clock](https://www.adafruit.com/product/3386)
based on the PCF8523 chip, so that the timestamps in the log files 
would be accurate. (This is a different realtime clock board than we
used on the Wall of JoCo. It is more convenient to install on a
Raspberry Pi.)

We used a [LG 24M38H](http://www.lg.com/us/monitors/lg-24M38H-B-led-monitor)
HDMI monitor at 1920x1080 ("Full HD" 1080P) resolution. Note that the Wall
is hard-coded for this resolution and will look terrible at any other 
resolution.

## Deployment Notes

### Operating System

We ran [Raspbian](http://raspbian.org) Jessie on a 32GB SD card. This 
was created using
[NOOBS](https://www.raspberrypi.org/blog/introducing-noobs/) 2.8.1 to 
install Raspbian Stretch.

### Permissions

The Wall needs networking permissions to operate the Bluetooth socket
interface. This could be accomplished by running as `root` but that's a
bad idea. Instead, we want to grant ourselves the appropriate capabilities.
But we're a script running under the Python interpreter, so actually we
needed to grant those capabilities to the interpreter. We didn't want to do
that for every Python program, so we made a private copy of the interpreter
and granted the capabilities to that. Like so:

```
	cp /usr/bin/python3 capython3
	sudo setcap 'cap_net_raw,cap_net_admin+eip' capython3
```

We then put that private interpreter in the shebang line at the top of
`walloftio.py`, so it gets the needed permissions if run like so:

```
	./walloftio.py
```

### Dependencies

```
	sudo apt-get install python3-pil.imagetk libnfc-dev
	sudo pip3 install gatt
	sudo pip install nfcpy subprocess32 wiringpi2
```

In addition, you'll need to have the font *Droid Sans Mono* installed
in one of the usual locations for fonts, such as ~/.fonts. A zip file
of this font is included. Unzip it and move the `.ttf` file to a fonts
directory.

Everything else needed was already included in the NOOBS install of
Raspbian. Note that this includes some dependencies that are only
needed if NFC is used as in the Wall of JoCo.

### Screen Blanking

We turned off screen blanking as suggested on
[this web page](http://www.geeks3d.com/hacklab/20160108/how-to-disable-the-blank-screen-on-raspberry-pi-raspbian/)
by adding

```
    [SeatDefaults]
    xserver-command=X -s 0 -dpms
```

in the file `/etc/lightdm/lightdm.conf `.

### Crash Recovery

If the Wall crashes or is killed after Bluetooth initialization, it can 
leave the interface(s) in an unusable condition. It can usually be recovered
like so:

```
	sudo hciconfig hci0 down
	sudo hciconfig hci0 up
```

If that doesn't work, a reboot probably will.

### Shell scripts and HCI Interfaces

The system auto-starts on boot by running `~/runwot.sh`. That in turns runs
`walloftio.py` in a terminal, so that it can display trace and error
information. The terminal is normally invisible behind the Wall display.
