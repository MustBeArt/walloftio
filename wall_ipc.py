# Simple text IPC to the Wall of JoCo

import socket

class WallIPC:
    sock = None
    
    def __init__(self, mac):
        print('IPC: opening window for %s' % mac)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def connect(self):
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.sock is not None:
            self.sock.connect(('localhost', 9999))

            
    def send(self, msg):
        print('IPC: %s' % msg)
        msg += '\n'
        sent_sofar = 0
        while sent_sofar < len(msg):
            sent = self.sock.send(msg[sent_sofar:])
            if sent == 0:
                self.sock.close()
                self.sock = None
                break
            sent_sofar += sent

    def close(self):
        print('IPC: closing window')
        self.sock.close()
