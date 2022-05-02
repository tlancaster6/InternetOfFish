# TODO: write reporter script
"""this script should take in status information from multiple pi's via socket connections to their watcher processes,
parse those status reports, and compile them into a human-readable format/file (possibly a file that is read-only
to the user, but writeable by this program?).

Should also notice when a particular host suddenly stops pinging, and potentially notify someone? probably easiest to
have the status reports include the email associated with each project, and set up a simple sendgrid notifier.

https://realpython.com/python-sockets/

"""

from internet_of_fish.modules.utils import gen_utils
import socket

LOOPBACK_HOST = "127.0.0.1"
PORT = 13221



class Reporter(metaclass=gen_utils.AutologMetaclass):

    def __init__(self):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_socket.bind((LOOPBACK_HOST, PORT))

    def main_loop(self):
        self.listening_socket.listen()
        conn, addr = self.listening_socket.accept()

    def main_func(self):
        s.listen()
        while True:
            c, addr = s.accept()
            print ('Got connection from', addr)
            c.send('Thank you for connecting'.encode())
            c.close()
            break





