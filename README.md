# Wall of JoCo aboard JoCo Cruise 2018

Brought to you by Abraxas3D and Skunkwrx.

Based on the [Wall of Bender](https://github.com/MustBeArt/wallofbender)


## Introduction

The **Wall of Joco** is a logger and display board for the
JOCO Cruise 2018 Pirate Monkey Badge. The badge has a Bluetooth Low Energy (BLE)
radio, which it uses to implement a game. Each badge is constantly transmitting its
unique ID, player name, and other game info in BLE advertisement format.
The Wall listens for these advertisements, logs them all to a file, and
displays them in a friendly format for the amusement and edification of
passers-by.

Three windows are displayed. A smaller window displays just the names and
unique IDs of each and every badge advertisement received, in real time,
even if they go by too fast to read. A bigger window displays the same
information plus a time-since-last-heard indication, and scrolls
the entire stored list, after removing duplicates based on the BLE
advertising address transmitted. In between, another scrolled
window shows just the names received, regardless of which badge sent them.

As the JoCo badge accumulates game points, it becomes eligible to receive
trinkets from a central dispenser station. The Wall includes a companion
process, Trinketctl, that controls trinket dispensing. The JoCo badge has
NFC hardware, and Trinketctl interfaces with an NFC reader. When the badge
is presented to the reader, Trinketctl initiates a sequence of events that
may lead to a trinket being dispensed, displaying messages and prompts in
a text window that pops up over the normal Wall display.

When Trinketctl detects an NFC device, it attempts to read NDEF data from
the detected device. The badge supplies its BLE MAC address, its 16-bit
device ID, and its name in the NDEF record. Immediately, Trinketctl opens
a TCP socket (port 9999) to the Wall, which causes the Wall to pop up the
overlay window for Trinketctl to use. Trinketctl sends a message greeting
the badge by name.

The next step is a local check within Trinketctl to limit the total number
of trinkets that can be dispensed to a single badge (assumed to be uniquely
identified by its BLE MAC address). Records for this check are kept in files
in the `trinket_log` directory, named for the BLE MAC address of the badge,
containing a timestamp line for each recorded trinket dispensed. If Trinketctl
finds an existing file with seven or more lines already recorded, it just
tells the badge that it already has all the trinkets, and terminates the
transaction.

Otherwise, Trinketctl next needs to find out whether the badge has earned
enough points to qualify for a trinket. The badge is entitled to a trinket
for each 250 points it earns in the game. In order to decide whether a new
trinket has been earned, Trinketctl needs the badge's current score and also
the number of trinkets already dispensed to that badge. It gets both by
reading a BLE GATT *characteristic* from the badge. To make it difficult
to cheat the dispenser, the characteristic is encrypted with AES-128, using
the same sort of scheme used by AND!XOR to encrypt state information on
their DC25 Bender badge.

If the encrypted information shows that the badge is eligible, Trinketctl
strobes a control line to the trinket dispenser, and watches for the
dispenser to respond with a busy signal on another line. Once the busy
signal goes away, Trinketctl assumes that a trinket has been successfully
dispensed. It initiates a further BLE GATT read of a special characteristic
that signals the badge to increment its internal counter of how many
trinkets it has received. This should have been a GATT write with more
encryption, but I was unable to get the GATT write to work. Using an
unprotected GATT read was a quick expedient at the inevitable last minute.


## Hardware

We deployed the Wall of Joco on a
[Raspberry Pi Zero W](https://www.raspberrypi.org/products/raspberry-pi-zero-w/).

The Raspberry Pi Zero W does not have an on-board realtime clock, so we added
an [Adafruit DS3231 Precision RTC Breakout](https://www.adafruit.com/product/3013) 
so that the timestamps in the log files would be accurate.

The Raspberry Pi Zero W  has its own built-in Bluetooth hardware. Because
of limitations in the software stacks we used for Bluetooth, it was convenient
to add an additional USB Bluetooth adapter, a Cirago BTA8000. The Wall
functions used the BTA8000 through the old socket-based interface to the
standard [BlueZ Bluetooth stack](http://www.bluez.org), whereas the
Trinketctl functions used the built-in Bluetooth through the modern D-Bus
interface to BlueZ, via the [Bluetooth GATT SDK for Python](https://github.com/getsenic/gatt-python).
I didn't find a way to run both on the same adapter, or to implement either
function using the other interface.

We used a [LG 24M38H](http://www.lg.com/us/monitors/lg-24M38H-B-led-monitor)
HDMI monitor at 1920x1080 ("Full HD" 1080P) resolution. Note that the Wall
of Joco is hard-coded for this resolution and will look terrible at any
other resolution.

The NFC hardware was an [Adafruit PN532 NFC/RFID controller breakout board](https://www.adafruit.com/product/364),
connected to the Raspberry Pi Zero W's serial port for data and to
GPIO 25 for reset.

The USB Bluetooth adapter, along with a Microsoft wireless keyboard/mouse
adapter for development, were plugged into the Raspberry Pi Zero W via an
unpowered [USB hub](https://www.adafruit.com/product/2991).

The trinket dispenser was created separately on its own microcontroller board.
It had two open-collector TTL-level interface signals (plus ground): a strobe
from GPIO 23 of the Raspberry Pi Zero W to command the dispenser to operate,
and a busy signal to GPIO 24 indicating that the dispenser motor was running.

All the hardware except the monitor was installed inside the trinket
dispenser base, with liberal application of hot glue.


## Deployment Notes

### Operating System

We ran [Raspbian](http://raspbian.org) Jessie on a 32GB SD card. This
began as a Wall of Bender installation, originally created using
[NOOBS](https://www.raspberrypi.org/blog/introducing-noobs/) 2.4.2 to install
on an 8GB SD card, which we then image copied onto a 32GB SD card. We expanded
the filesystem, and morphed it into the Wall of Joco.

### Permissions

The Wall of Joco needs networking permissions to operate the Bluetooth socket
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
`wallofjoco.py`, so it gets the needed permissions if run like so:

```
	./wallofjoco.py
```

### Dependencies

```
	sudo apt-get install python3-pil.imagetk libnfc-dev
	sudo pip3 install gatt
	sudo pip install nfcpy subprocess32
```

Everything else needed was already included in the NOOBS install of
Raspbian. I think. I haven't gone back and tested this dependency list.

### Connecting the NFC Hardware

See [Adafruit NFC/RFID on Raspberrry Pi](https://learn.adafruit.com/adafruit-nfc-rfid-on-raspberry-pi)
for info on connecting the NFC hardware to the Raspberry Pi Zero W.

We used the built-in serial port on the Raspberry Pi Zero W to talk to the
PN532 in UART mode. In order to do that, we had to disable the serial console
and enable the serial port, as described in the Adafruit documentation.

Besides the serial port interface, we also connected a wire from GPIO pin 25
on the Raspberry Pi Zero W to the reset pin RSTPD_N on the NFC Breakout.
A separate Python script, `resetnfc.py`, was written to strobe the reset pin.
This script is called from the shell script that starts (and re-starts) the
system, to clear occasional wedged states the PN532 seems prone to get into.

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
	sudo hciconfig hci1 down
	sudo hciconfig hci1 up
```

If that doesn't work, a reboot probably will.

If the NFC hardware gets confused, run resetnfc.py. If that doesn't work,
you'll probably have to power cycle the whole system.

### Dispenser Emulation

Since the actual dispenser hardware wasn't available until the last day
before the cruise's departure, I wrote a little Arduino sketch to emulate
its behavior with respect to Trinketctl, `dispenser-emu.ino`.

### GATT Transaction Implementation

The GATT library needed Python 3 to run. The NFC library, on the other hand,
needed Python 2 and didn't support Python 3. In order to work around this
incompatibility, the GATT transactions were put into separate scripts,
`badge_gatt_score.py` and `badge_gatt_lldi.py`, running in Python 3, and
they were called using the [subprocess32 module](https://github.com/google/python-subprocess32).

### Shell scripts and HCI Interfaces

The system auto-starts on boot by running `~/runwoj.sh`. That in turns runs
`~/runwoj2.sh` in a terminal, so that it can display trace and error
information. The terminal is normally invisible behind the Wall display.
For developer convenience, `runwoj2.sh` launches another (unused) terminal,
also hidden.

`runwoj2.sh` runs and, if necessary, re-runs the Wall and Trinketctl
scripts. As a precaution against wedged hardware, it resets the NFC board
before running Trinketctl. Besides that, it also does an ugly little dance
with the Bluetooth interfaces in order to arrange for the right process to
run on the right Bluetooth adapter. The system enumerates the USB dongle
first, so the BTA8000 is named hci0 and the built-in Bluetooth hardware is
named hci1.

I could tell the GATT library functions which adapter to use, but I couldn't
find a way to control which interface was used by the socket-based
Bluetooth code in the Wall. It always used the most recently enumerated
interface, hci1. Unfortunately, the built-in Broadcom Bluetooth hardware
seems to be incompatible with the GATT library, so I needed to reserve hci1
for Trinketctl. So, the script calls `rfkill` to block hci1 before it
runs the Wall. Since it runs the Wall as a background process, it has no
good way to know when the Wall has finished initializing (and picking its
Bluetooth adapter), so it just waits for a fixed 30 seconds. Then it unblocks
hci1 before running Trinketctl in the foreground. Luckily, the socket code
in the Wall doesn't ever seem to switch adapters once it has initialized one.

If Trinketctl ever exits, the script tries to kill off the Wall process too
and then loops, in the hope of getting everything back up and working
automatically.