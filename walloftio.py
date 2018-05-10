#!./capython3
# To avoid running as root, we use a copy of the Python3 interpreter.
# Give it the needed capabilities with this command:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' capython3

# Portions of the Bluetooth interaction parts of this script have been
# taken from https://stackoverflow.com/questions/23788176/finding-bluetooth-low-energy-with-python


import sys
import os
import struct
import signal
import time
import errno
from ctypes import (CDLL, get_errno)
from ctypes.util import find_library
from socket import (
    socket,
    AF_BLUETOOTH,
    AF_INET,
    SOCK_RAW,
    SOCK_STREAM,
    BTPROTO_HCI,
    SOL_HCI,
    HCI_FILTER,
)
from tkinter import *
from PIL import ImageTk, Image
from collections import deque
import threading
import gatt
import joco_crypto
import random

wait_factor = 50

# With this address set to localhost, the socket should not be visible
# to hosts on the network, just from the local machine.
termaddr = ("localhost", 9999)

BADGE_TYPE_JOCO = 0x0b25
BADGE_TYPE_ANDNXOR = 0x049e

BADGE_YEAR = "yr"     # year (Appearance field) in most recent advertisement
BADGE_YEARS = "yrs"   # list of years seen for this address
BADGE_NAME = "nm"     # badge name (Complete Local Name) in most recent
BADGE_NAMES = "nms"   # list of names seen for this address
BADGE_ID = "id"       # badge ID (first two octets of Manufacturer Specific Data)
BADGE_IDS = "ids"     # list of badge IDs seen for this address
BADGE_TIME = "tm"     # time of most recent advertisement received
BADGE_ADDR = "ad"     # Advertising Address for this badge (assumed constant)
BADGE_CNT = "n"       # number of advertisements received from this address
BADGE_ID_FAKED = "faked"    # present if multiple IDs seen for this address
BADGE_CTRINKET = "tkt"    # claimed to deserve a trinket
BADGE_CSCORE = "csc"  # claimed current score
BADGE_TYPE = "ty"     # Badge type (Company ID)

MAIN_DISPLAY_FONTSIZE = 40


class BTAdapter (threading.Thread):
    def __init__(self, master, btQueue):
        threading.Thread.__init__(self)
        self.btQueue = btQueue

        self.stop_event = threading.Event()

        btlib = find_library("bluetooth")
        if not btlib:
            raise Exception(
                "Can't find required bluetooth libraries"
                " (need to install bluez)"
            )
        self.bluez = CDLL(btlib, use_errno=True)

        dev_id = self.bluez.hci_get_route(None)
        
        self.sock = socket(AF_BLUETOOTH, SOCK_RAW, BTPROTO_HCI)
        if not self.sock:
            print("Failed to open Bluetooth")
            sys.exit(1)

        self.sock.bind((dev_id,))

        err = self.bluez.hci_le_set_scan_parameters(self.sock.fileno(), 0, 0x10, 0x10, 0, 0, 1000)
        if err < 0:
            raise Exception("Set scan parameters failed")
            # occurs when scanning is still enabled from previous call

        # allows LE advertising events
        hci_filter = struct.pack(
            "<IQH",
            0x00000010,
            0x4000000000000000,
            0
        )
        self.sock.setsockopt(SOL_HCI, HCI_FILTER, hci_filter)

        err = self.bluez.hci_le_set_scan_enable(
            self.sock.fileno(),
            1,    # 1 - turn on;  0 - turn off
            0,    # 0-filtering disabled, 1-filter out duplicates
            1000  # timeout
        )
        if err < 0:
            errnum = get_errno()
            raise Exception("{} {}".format(
                errno.errorcode[errnum],
                os.strerror(errnum)
            ))

    def stop(self):
        self.stop_event.set()

    def stopped(self):
        return self.stop_event.is_set()

    def clean_up(self):
        if self.sock is None:
            print("Double clean_up", flush=True)
            return

        err = self.bluez.hci_le_set_scan_enable(
            self.sock.fileno(),
            0,    # 1 - turn on;  0 - turn off
            0,    # 0-filtering disabled, 1-filter out duplicates
            1000  # timeout
            )
        if err < 0:
            errnum = get_errno()
            print("{} {}".format(
                errno.errorcode[errnum],
                os.strerror(errnum)
                ))

        self.sock.close()
        self.sock = None

    def run(self):
        while True:
            data = self.sock.recv(1024)
            badge_time = time.time()
            self.btQueue.appendleft((badge_time, data))
            if self.stopped():
                self.clean_up()
                break


class Logger:
    def __init__(self):
        self.intercepts = []
        self.count = 0

    def _writeout(self):
        filename = time.strftime("%Y%m%d%H%M%S", time.gmtime(time.time())) + ".log"
        with open(filename, "w+") as f:
            for ts, data in self.intercepts:
                hex = ''.join('{0:02x}'.format(x) for x in data)
                print("%f %s" % (ts, hex), file=f)

    def intercept(self, cept):
        self.intercepts.append(cept)
        self.count += 1
        if self.count >= 1000:
            self._writeout()
            self.intercepts = []
            self.count = 0

    def closeout(self):
        self._writeout()


class LiveDisplay:
    def __init__(self, master):
        self.live_canvas = Canvas(master, width=370, height=505, bg=tablebg, borderwidth=0, highlightthickness=0)
        self.live_text = self.live_canvas.create_text(tmargin, tmargin, anchor=NW, text="", font=("Droid Sans Mono", 32))
        self.live_canvas.place(x=screenw-margin, y=screenh-margin, anchor=SE)
        self.lines = deque()

    def intercept(self, badge):
        line = "%s %s" % (badge[BADGE_ID], badge[BADGE_NAME])
        self.logtext(line)

    def logtext(self, text):
        if len(self.lines) >= 10:
            self.lines.popleft()
        self.lines.append(text)
        self.live_canvas.itemconfigure(self.live_text, text="\n".join(self.lines))


class SmoothScroller:
    def __init__(self, master, width, height, x, y, wait):
        self.master = master
        self.wait = wait * wait_factor
        self.height = height
        self.canvas = Canvas(master, width=width, height=height, bg=tablebg, borderwidth=0, highlightthickness=0)
        self.text = self.canvas.create_text(tmargin, tmargin, anchor=NW, text="", font=("Droid Sans Mono", MAIN_DISPLAY_FONTSIZE))
        self.canvas.place(x=x, y=y, anchor=NW)
        self.scroll()

    def scroll(self):
        left, top, right, bottom = self.canvas.bbox(ALL)
        if bottom > self.height:
            self.canvas.move(self.text, 0, -wait_factor)
        elif top < 0:
            if bottom > 0:
                self.canvas.move(self.text, 0, -wait_factor)
            else:
                self.canvas.move(self.text, 0, -top + self.height)
        self.master.after(self.wait, self.scroll)


class NamesDisplay (SmoothScroller):
    def __init__(self, master):
        SmoothScroller.__init__(self, master, width=265, height=680, x=margin+1080+margin, y=350, wait=20)
        self.lines = deque()
        self.scroll()

    def intercept(self, badge):
        if badge[BADGE_NAME] not in self.lines:
            # print("BADGE NAME .%s." % badge[BADGE_NAME])
            # line = badge[BADGE_NAME] + " "*(8-len(badge[BADGE_NAME]))
            # print("LINE .%s." % line)
            self.lines.append(badge[BADGE_NAME])
            self.canvas.itemconfigure(self.text, text="\n".join(self.lines))


class BadgeDisplay (SmoothScroller):
    def __init__(self, master):
        self.master = master
        self.badges = {}
        SmoothScroller.__init__(self, master, width=1080, height=750, x=margin, y=275, wait=30)
        self.lines = deque()
        self.scroll()
        self.updater()

    def updater(self):
        self.update_display()
        self.master.after(5000, self.updater)

    def format_time_ago(self, t, timenow):
        age = timenow - t
        if age < 5.0:
            return " just now"
        else:
            hours = int(age / (60*60))
            age -= hours * 60*60
            minutes = int(age / 60)
            age -= minutes * 60
            secs = int(age/5) * 5
            if hours > 0:
                return "%3d:%02d:%02d" % (hours, minutes, secs)
            else:
                return "    %2d:%02d" % (minutes, secs)

    def update_display(self):
        timenow = time.time()
        self.lines = []
        for b in sorted(self.badges.values(), key=lambda badge: badge[BADGE_CSCORE], reverse=True):
            if BADGE_ID_FAKED in b:
                flag = "*"
            else:
                flag = " "
            ident = b[BADGE_ID]
            name = b[BADGE_NAME]
            typ = b[BADGE_TYPE]
            if typ == BADGE_TYPE_JOCO:
                if b[BADGE_CSCORE] >= 1000:
                    score = "%2d,%03d" % (b[BADGE_CSCORE]/1000, b[BADGE_CSCORE] % 1000)
                else:
                    score = " %5d" % b[BADGE_CSCORE]
                if b[BADGE_CTRINKET] != 0:   # claims to be eligible for a trinket
                    flag = "!"
            else:
                score = "   N/A"
            t = self.format_time_ago(b[BADGE_TIME], timenow)
            line = flag + " " + ident + " " + name + " "*(8-len(name)) + " " + score + " " + t
            self.lines.append(line)
        self.canvas.itemconfigure(self.text, text="\n".join(self.lines))

    def intercept(self, badge):
        if badge[BADGE_ADDR] not in self.badges:
            badge[BADGE_IDS] = [badge[BADGE_ID]]
            badge[BADGE_NAMES] = [badge[BADGE_NAME]]
            badge[BADGE_YEARS] = [badge[BADGE_YEAR]]
            badge[BADGE_CNT] = 1
            self.badges[badge[BADGE_ADDR]] = badge
            # do not call self.update_display()

        else:
            b = self.badges[badge[BADGE_ADDR]]
            b[BADGE_CNT] += 1
            b[BADGE_NAME] = badge[BADGE_NAME]
            b[BADGE_ID] = badge[BADGE_ID]
            b[BADGE_TIME] = badge[BADGE_TIME]
            b[BADGE_YEAR] = badge[BADGE_YEAR]
            if badge[BADGE_NAME] not in b[BADGE_NAMES]:
                b[BADGE_NAMES].append(badge[BADGE_NAME])
            if badge[BADGE_ID] not in b[BADGE_IDS]:
                b[BADGE_IDS].append(badge[BADGE_ID])
            if badge[BADGE_YEAR] not in b[BADGE_YEARS]:
                b[BADGE_YEARS].append(badge[BADGE_YEAR])
            if len(b[BADGE_IDS]) > 1:
                b[BADGE_ID_FAKED] = True
            b[BADGE_CTRINKET] = badge[BADGE_CTRINKET]
            b[BADGE_CSCORE] = badge[BADGE_CSCORE]
            # do not call self.update_display()


class TermDisplay:
    def __init__(self, master):
        self.term_canvas = Canvas(master, width=1200, height=750, bg=termbg, borderwidth=0, highlightthickness=0)
        self.term_text = self.term_canvas.create_text(widemargin, widemargin, anchor=NW, text="", font=("Droid Sans Mono", 48))
        self.lines = deque()
        self.showing = False
        
    def show(self):
        if not self.showing:
            self.term_canvas.place(x=1920/2, y=1024/2, anchor=CENTER)
            self.showing = True

    def hide(self):
        if self.showing:
            self.term_canvas.place_forget()
            self.showing = False
        
    def logtext(self, text):
        if len(self.lines) >= 14:
            self.lines.popleft()
        self.lines.append(text)
        self.term_canvas.itemconfigure(self.term_text, text="\n".join(self.lines))

    def clear(self):
        self.lines.clear()

class BadgeDevice(gatt.Device):
    def connect_succeeded(self):
        super().connect_succeeded()
        live_display.logtext("Connected")

    def connect_failed(self, error):
        super().connect_failed(error)
        live_display.logtext("Failed")

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        live_display.logtext("Disconnected")

    def services_resolved(self):
        super().services_resolved()
        score_service = next(
            s for s in self.services
            if s.uuid == '0000bd7e-0000-1000-8000-00805f9b34fb')
        encrypted_score = next(
            c for c in score_service.characteristics
            if c.uuid == '00002e15-0000-1000-8000-00805f9b34fb')
        encrypted_score.read_value()
        live_display.logtext("Reading")

    def characteristic_value_update(self, characteristic, value):
        result = joco_crypto.eval_score_characteristic(value)
        if result is None:
            live_display.logtext("Invalid")
        else:
            live_display.logtext("%s %d %d" % result)
        device.disconnect()
        manager.stop()

    def characteristic_read_value_failed(self, characteristic, error):
        live_display.logtext("Read failed.")


margin = 50
tmargin = 5
widemargin = 40
screenh = 1080
screenw = 1920
bgcolor = "#ffe298"
tablebg = "#eed288"
termbg = "#00ff00"

root = Tk()
root.overrideredirect(True)
root.overrideredirect(False)
root.attributes("-fullscreen", True)
root.configure(background=bgcolor)

heading = Label(root, text="Wall of JoCo", bg=bgcolor, font=("Droid Sans Mono", 120))
heading.place(x=margin, y=margin-40, anchor=NW)
credit = Label(root, text="Brought to you by Phase4Ground with thanks to AND!XOR",
               fg="#888888", bg=bgcolor, font=("Droid Sans Mono", 9))
credit.place(x=margin+18, y=170, anchor=NW)
badges_label = Label(root, text="   ID  Name      Score      Seen", bg=bgcolor, font=("Droid Sans Mono", MAIN_DISPLAY_FONTSIZE))
badges_label.place(x=margin, y=210, anchor=NW)
names_label = Label(root, text="Names", bg=bgcolor, font=("Droid Sans Mono", 50))
names_label.place(x=margin+1085+margin, y=265, anchor=NW)
live_label = Label(root, text="Intercepts", bg=bgcolor, font=("Droid Sans Mono", 44))
live_label.place(x=margin+912+margin+435+margin, y=460, anchor=NW)

img = ImageTk.PhotoImage(Image.open("badge_photo.png").convert("RGBA"))
photo_panel = Label(root, image=img, borderwidth=0, bg=bgcolor)
photo_panel.place(x=screenw-margin/2, y=margin/2, anchor=NE)

badge_display = BadgeDisplay(root)
names_display = NamesDisplay(root)
live_display = LiveDisplay(root)
term_display = TermDisplay(root)
log = Logger()


def click_callback(event):
    live_display.logtext("Click!")
    term_display.show()
    term_display.logtext("random %d" % random.randint(1,10000))
    #manager = gatt.DeviceManager(adapter_name='hci1') # separate adapter
    #device = BadgeDevice(mac_address='e2:15:e5:53:f2:0c', manager=manager)
    #device.connect()
    #manager.run()
    live_display.logtext("Done.")

def rclick_callback(event):
    live_display.logtext("Right click!")
    term_display.hide()
    term_display.clear()

photo_panel.bind("<Button-1>", click_callback)
photo_panel.bind("<Button-3>", rclick_callback)
                  
def badgeParse(data):
    """ If the advertisement data contains a valid badge beacon,
    return the parsed badge data structure. If not, return None."""

    badge_address = ':'.join('{0:02x}'.format(x) for x in data[12:6:-1])

    index = 14
    badge = False
    badge_name = None
    while (index < len(data)-1):
        packet_len = data[index]
        packet_type = data[index+1]
        packet_payload = data[index+2:index+2+packet_len-1]
        index += packet_len+1
        if packet_type == 0x01:     # Flags
            if int(packet_payload[0]) != 0x06:
                badge = False
        elif packet_type == 0x09:   # Local Name
            badge_name = packet_payload.decode("utf-8").upper()
        elif packet_type == 0x19:   # Appearance
            badge_year = "%02X%d" % (packet_payload[0], packet_payload[1])
        elif packet_type == 0xFF:   # Manufacturer Specific Data
            badge_type = (packet_payload[1] << 8) + packet_payload[0]
            if badge_type == BADGE_TYPE_JOCO:
                badge_id = "%02X%02X" % (packet_payload[3], packet_payload[2])
                badge_claimed_score = (packet_payload[4] << 8) + packet_payload[5]
                badge_claimed_trinket = badge_claimed_score & 0x8000
                badge_claimed_score = badge_claimed_score & 0x7FFF
                badge = True
            elif badge_type == BADGE_TYPE_ANDNXOR:
                badge_id = "%02X%02X" % (packet_payload[3], packet_payload[2])
                badge_claimed_trinket = 0
                badge_claimed_score = -1   # so it always sorts below JoCo badges
                badge = True
            else:
                badge = False

    if badge and badge_name is not None and badge_year is not None:
        return {BADGE_ADDR:   badge_address,
                BADGE_ID:     badge_id,
                BADGE_NAME:   badge_name,
                BADGE_YEAR:   badge_year,
                BADGE_CTRINKET:   badge_claimed_trinket,
                BADGE_CSCORE: badge_claimed_score,
                BADGE_TYPE:   badge_type}
    else:
        return None


def processAdvertisement(cept):
    timestamp, data = cept
    badge = badgeParse(data)
    if badge is not None:
        badge[BADGE_TIME] = timestamp
        live_display.intercept(badge)
        names_display.intercept(badge)
        badge_display.intercept(badge)
        log.intercept(cept)


def signal_handler(signal, frame):
    bt.stop()
    log.closeout()
    root.quit()


def btPoller():
    while True:
        try:
            intercept = btQueue.pop()
            processAdvertisement(intercept)

        except IndexError:
            break

    root.after(100, btPoller)


def terminal_thread():
    global termsocket, term_display
    while True:
        (sock, address) = termsocket.accept()       # blocking
        term_display.show()
        stuff = sock.recv(512)
        while len(stuff) != 0:
            for line in stuff.decode('ascii').splitlines():
                term_display.logtext(line)
            stuff = sock.recv(512)
        term_display.hide()
        term_display.clear()


termsocket = socket(AF_INET, SOCK_STREAM)
termsocket.bind(termaddr)
termsocket.listen(5)
termthread = threading.Thread(target=terminal_thread)
termthread.start()

btQueue = deque(maxlen=1000)
bt = BTAdapter(root, btQueue)
bt.start()
signal.signal(signal.SIGINT, signal_handler)
btPoller()
root.mainloop()
