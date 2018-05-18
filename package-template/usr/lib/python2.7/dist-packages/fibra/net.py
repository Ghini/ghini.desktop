"""
This module defines low level tasks for working with sockets.

"""
import socket
import struct
import time

from fibra.handlers.tasks import Return, Async
from fibra.handlers.io import Read, Write, Close
from fibra.handlers.nonblock import Unblock


BUFFER_SIZE = 1024 * 1024 
MAX_FRAME_SIZE = 1024*1024
DEFAULT_TIMEOUT = 60.0



class Shutdown(Exception): pass


def listen(address, accept_task, listen_task=None):
    """Listen on address, and spawn accept_task when a connection is received."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    if listen_task is not None: yield Async(listen_task(sock))
    while True:
        yield Read(sock)
        yield Async(accept_task(Transport(sock.accept()[0])))


def connect(address, timeout=1):
    """Connect to address, and Return a transport on success."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    yield Unblock()
    sock.connect(address)
    sock.setblocking(0)
    yield Write(sock, timeout)
    yield Return(Transport(sock, address))

    
class Transport(object):
    """Provides methods for sending and receiving bytes, lines and frames
    over a socket.
    """
    def __init__(self, sock, address=None):
        self.sock = sock
        self.address = address
        self.stream = ""
        self.aborted = False

    def _fetch(self, timeout=DEFAULT_TIMEOUT):
        if self.aborted: raise Shutdown('clean shutdown')
        yield Read(self.sock, timeout)    
        data = self.sock.recv(BUFFER_SIZE)
        if data == "":
            yield self.close()
        else:
            self.stream += data 

    def close(self):
        self.aborted = True
        yield Close(self.sock)
        self.sock.close()

    def recv(self, size, timeout=DEFAULT_TIMEOUT):
        """Receive a number of bytes."""
        while len(self.stream) < size:
            yield self._fetch()
        msg = self.stream[:size]
        self.stream = self.stream[size:]
        yield Return(msg)
                
    def recv_frame(self, timeout=DEFAULT_TIMEOUT):
        """Receive a frame (a size prefixed string)."""
        while len(self.stream) < 4:
            yield self._fetch()
        size, = struct.unpack("!i", self.stream[:4])
        self.stream = self.stream[4:]
        if size > MAX_FRAME_SIZE: raise socket.error
        while len(self.stream) < size:
            yield self._fetch()
        msg = self.stream[:size]
        self.stream = self.stream[size:] 
        yield Return(msg)

    def recv_line(self, terminator="\n", strip=True, timeout=DEFAULT_TIMEOUT):
        """Receive a line terminated by terminator (default \n)"""
        while terminator not in self.stream:
            yield self._fetch()
        index = self.stream.index(terminator)
        line = self.stream[:index]
        self.stream = self.stream[index+len(terminator):]
        if strip: line = line.strip()
        yield Return(line)

    def send(self, data, timeout=DEFAULT_TIMEOUT):
        """Send data through a socket. Task does not finish until all data is sent."""
        while data: 
            yield Write(self.sock, timeout)
            c = self.sock.send(data)
            data = data[c:]

    def send_frame(self, msg, timeout=DEFAULT_TIMEOUT):
        """Send a frame (a size prefixed string) through a socket."""
        size = struct.pack("!i", len(msg))
        yield self.send(size+msg, timeout)

    def send_line(self, data, terminator="\n", timeout=DEFAULT_TIMEOUT):
        """Send data with a terminator through a socket."""
        yield self.send(data+terminator, timeout)

