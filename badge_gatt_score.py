#!./capython3

import gatt
import sys
import codecs
import argparse
import joco_crypto

debug_flag = False
badge_device = None

class BadgeDevice(gatt.Device):
    def connect_succeeded(self):
        super().connect_succeeded()
        if debug_flag:
            print('Connected')

    def connect_failed(self, error):
        super().connect_failed(error)
        if debug_flag:
            print('[%s] connection failed: %s' % (self.mac_address, str(error)))
        else:
            print("zzzz 0 0");
        manager.stop()
        sys.exit(1)
        

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        if debug_flag:
            print('Disconnected')
        manager.stop()
        sys.exit(1)
        
    def services_resolved(self):
        super().services_resolved()
        if debug_flag:
            print('resolved services')
            for s in self.services:
                print("service %s" % s.uuid)
        
        score_service = next(
            s for s in self.services
            if s.uuid == '0000bd7e-0000-1000-8000-00805f9b34fb')

        if debug_flag:
            for c in score_service.characteristics:
                print('characteristic %s' % c.uuid)
            
        encrypted_score = next(
            c for c in score_service.characteristics
            if c.uuid == '00002e15-0000-1000-8000-00805f9b34fb')

        encrypted_score.read_value()
        if debug_flag:
            print('started to read [%s]' % encrypted_score.uuid)

    def characteristic_value_updated(self, characteristic, value):
        if debug_flag:
            print("Encrypted score: ", codecs.encode(value, 'hex'))
        joco_crypto.customize_cipher(device_id)
        result = joco_crypto.eval_score_characteristic(value)
        if result is None:
            if debug_flag:
                print("Score decrypted invalid.")
            else:
                print("zzzz 0 0")
        else:
            if debug_flag:
                print("Device ID: %s Score: %d LLD: %d" % result)
            else:
                print("%s %d %d" % result)
        badge_device.disconnect()
        manager.stop()
 #       sys.exit()

    def characteristic_read_value_failed(self, characteristic, error):
        if debug_flag:
            print("[%s] read failed: %s" % (characteristic, str(error)));
        else:
            print("zzzz 0 0")
        manager.stop()
        sys.exit(1)


class AnyDeviceManager(gatt.DeviceManager):
    found = False
    
    def device_discovered(self, discovered_device):
        global badge_device
        
        if not self.found:
            if discovered_device.mac_address == args.gapAddress.lower():
                if debug_flag:
                    print("Discovered the badge.")
                self.stop_discovery()  # does not stop
                self.found = True
                badge_device = BadgeDevice(mac_address=args.gapAddress, manager=self)
                badge_device.connect()
            else:
                if debug_flag:
                    print("[%s] Discovered, alias = %s" %
                          (discovered_device.mac_address,
                           discovered_device.alias()))
            

parser = argparse.ArgumentParser(description='Get badge score info via encrypted GATT.')
parser.add_argument('--adapter', default='hci1')
parser.add_argument('--gapAddress', required=True)
parser.add_argument('--deviceID', required=True)
parser.add_argument('--debug', default=False, action='store_const', const=True)
args = parser.parse_args()

debug_flag = args.debug
if debug_flag:
    print("Args =", args)

device_id = int(args.deviceID[0:2], 16) + (int(args.deviceID[2:4], 16) << 8)
manager = AnyDeviceManager(adapter_name=args.adapter)
manager.start_discovery()
# device = BadgeDevice(mac_address=args.gapAddress, manager=manager)
# device.connect()

manager.run()
