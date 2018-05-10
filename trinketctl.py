#!/usr/bin/python2

import nfc
from nfc.clf import RemoteTarget
import signal
import RPi.GPIO as GPIO
from datetime import datetime
import wall_ipc
from wiringpi2 import millis, delay
from subprocess32 import check_output, CalledProcessError, TimeoutExpired

max_trinkets = 7
dispenser_strobe_pin = 23
dispenser_busy_pin = 24
dispenser_start_wait_ms = 200
dispenser_finish_wait_ms = 15000
window_close_delay_ms = 5000

GPIO.setmode(GPIO.BCM)


def pulse_dispenser():
    GPIO.setup(dispenser_strobe_pin, GPIO.OUT, initial=GPIO.LOW)
    # do we need a delay here? No, it's 10 uS or more already.
    GPIO.setup(dispenser_strobe_pin, GPIO.IN)        # Hi-Z


def check_dispenser_idle():
    GPIO.setup(dispenser_busy_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    return GPIO.input(dispenser_busy_pin)


def await_dispenser_start():
    timeout_time = millis() + dispenser_start_wait_ms
    while GPIO.input(dispenser_busy_pin) and millis() < timeout_time:
        pass
    return not GPIO.input(dispenser_busy_pin)


def await_dispenser_done():
    timeout_time = millis() + dispenser_finish_wait_ms
    while GPIO.input(dispenser_busy_pin) == 0 and millis() < timeout_time:
        pass
    return GPIO.input(dispenser_busy_pin)


def trinket_limit(mac):
    filename = 'trinket_log/'+mac
    try:
        with open(filename, 'rb') as f:
            lines = len(f.readlines())
    except IOError:
        print("No file")
        lines = 0
    return lines < max_trinkets


def trinket_log(mac):
    filename = 'trinket_log/'+mac
    stamp = datetime.now().isoformat()
    with open(filename, 'a+b') as f:
        f.write(stamp+'\n')


def get_badge_info(mac, device_id):
    # returns score, last_level_dispensed
    # score None means no transaction took place
    try:
        result = check_output(("./badge_gatt_score.py",
                                             "--gapAddress", mac,
                                             "--deviceID", device_id),
                              timeout=30)
        (devid, score, lld) = result.split()
        if devid.lower() == device_id.lower():
            return (score, lld)
        else:
            print("Device ID mismatch. NFC: %s GATT: %s" % (device_id, devid))
    except (CalledProcessError, TimeoutExpired):
        pass
    return (None, None)


def put_badge_lld(lld):
    # returns False if the badge couldn't be updated
    print("Updating LLD to %d" % lld)
    return True


def badge_increment_lld(mac):
    try:
        result = check_output(("./badge_gatt_lldi.py",
                               "--gapAddress", mac),
                              timeout=30)
    except (CalledProcessError, TimeoutExpired):
        return False

    return True



def talk_to_badge(nfc_msg):
    name = nfc_msg[16:].split('\x00', 1)[0]
    mac = ':'.join((nfc_msg[10:12], nfc_msg[8:10], nfc_msg[6:8],
                    nfc_msg[4:6], nfc_msg[2:4], nfc_msg[0:2]))
    device_id = ''.join((nfc_msg[14:16], nfc_msg[12:14]))
    ipc = wall_ipc.WallIPC(mac)
    ipc.connect()
    ipc.send("Welcome %s!" % name)
    ipc.send("")
    ipc.send("Checking your score ...")
    print('Talking to %s' % mac)
    eligible = trinket_limit(mac)
    if not eligible:
        print('%s not eligible for more trinkets!' % mac)
        ipc.send("You have all the trinkets!")
        trinket_log(mac)    # Log extra attempts just for fun
    else:
        (score, lld) = get_badge_info(mac, device_id)
        if score is not None:
            score = int(score)
            lld = int(lld)
            print "GATT reported score=%d lld=%d" % (score, lld)
            if score is not None:
                ipc.send("Your score is %d" % score)
                if score < (lld+1)*250:
                    ipc.send("Try again when it reaches %d" % ((lld+1)*250))
                else:
                    ipc.send("Eligible for a trinket!")
                    if check_dispenser_idle():
                        pulse_dispenser()
                        if await_dispenser_start():
                            ipc.send("Here's a gift for you!")
                            if await_dispenser_done():
                                ipc.send("Please take your gift")
                                trinket_log(mac)
                                # put_badge_lld(lld+1)
                                if not badge_increment_lld(mac):
                                    ipc.send("Where did you go?")
                            else:
                                ipc.send("Oops, I'm broken!")
                                ipc.send("Please ask for help")
                        else:
                            ipc.send("Dispenser not responding")
                            ipc.send("Try again later")
                    else:
                        ipc.send("Dispenser busy!")
                        ipc.send("Try again later")
        else:
            ipc.send("Where did you go?")
            
    delay(window_close_delay_ms)
    ipc.close()


def on_NFC_connect(tag):
    if tag.ndef is not None:
        try:
            nfc_msg = next(
                rec.text for rec in tag.ndef.records
                if ((rec.encoding == 'UTF-8') and (rec.language == 'en')))
            talk_to_badge(nfc_msg)
        except StopIteration:
            print("No matching records found.")
    return True


def on_NFC_release(tag):
    print("Released.")


def on_SIGHUP_handler(signalnum, frame):
    global running
    running = False


running = True
signal.signal(signal.SIGHUP, on_SIGHUP_handler)

print("Waiting for NFC appearance.")

with nfc.ContactlessFrontend('tty:S0:pn532') as clf:
    while running:
        # Wrapping clf.connect in a try block doesn't work.
        clf.connect(targets=('106A'),
                    rdwr={'on-connect': on_NFC_connect,
                          'on-release': on_NFC_release})
        print("Trying again!")
