"""
The fibra.event module provides pubsub style functions
for tasks over TCP.
"""

import fibra
import fibra.net

import socket
import sys
import traceback


schedule = fibra.schedule()

class Connection(object):
    """
    A base connection class for fibra.event.
    """
    def __init__(self, transport):
        self.running = True
        self.protocol = Protocol(transport)
        self.outbox = fibra.Tube()
        schedule.install(self.start())

    def start(self):
        yield fibra.Async(self.receiver())
        yield fibra.Async(self.sender())

    def on_connect(self):
        yield None

    def on_close(self):
        yield None

    def send(self, top, headers, body=""):
        if body:
            headers["content-length"] = "%s"%len(body)
        else:
            if "content-length" in headers:
                headers.pop("content-length")
        return self.outbox.push((top, headers, body))

    def sender(self):
        while self.running:
            try:
                top, headers, body = yield self.outbox.pop()
            except fibra.ClosedTube:
                break
            try:
                yield self.protocol.send(top, headers, body)
            except Exception, e:
                print "Connection lost while sending:", type(e), e
                break

        yield self.close()
        
    def receiver(self):
        while self.running:
            try:
                top, headers, body = yield self.protocol.recv()
            except fibra.net.Shutdown:
                break
            except Exception, e:
                print "Connection lost while receiving:", type(e), e
                break
            try:
                yield self.dispatch(top, headers, body)
            except Exception, e:
                print "Exception caught in method:", type(e), e
                print "Arguments:", top, headers, body
                break
        yield self.outbox.close()
        yield self.close()

    def dispatch(self, top, headers, body):
        method = getattr(self, 'do_%s'%top, None)
        if method is not None:
            return method(headers, body)
        else:
            raise AttributeError("Uknown method: %s"%top)

    def close(self):
        if self.running:
            self.running = False
            yield self.on_close()
            yield self.protocol.close()


class Protocol(object):
    """
    A line based protocol for fibra.event.
    """
    def __init__(self, transport):
        self.transport = transport

    def recv(self):
        top = yield self.transport.recv_line()
        headers = yield self.collect_headers()
        try:
            size = int(headers.get('content-length', ""))
        except ValueError:
            body = "" 
        else:
            body = yield self.transport.recv(size)
        yield fibra.Return((top, headers, body))

    def send(self, top, headers, body=""):
        if body:
            headers['content-length'] = "%s"%len(body)
        data = top + "\n" + "\n".join(":".join(i) for i in headers.items()) + "\n\n" + body
        yield self.transport.send(data)
            
    def collect_headers(self):
        headers = {}
        while True:
            line = yield self.transport.recv_line()
            if line == "": break
            i = line.index(":")
            k, v = line[:i].lower(), line[i+1:]
            headers[k] = v
        yield fibra.Return(headers)

    def close(self):
        return self.transport.close()


def serve(address, connection_class, on_listen=None):
    """
    This task listens for connections on a address.
    """
    def accept_task(transport):
        client = connection_class(transport)
        yield client.on_connect()
    yield fibra.net.listen(address, accept_task, listen_task=on_listen)


def connect(address, connection_class, retry=0):
    """
    This tasks connects to a server.
    """
    transport = None
    sleep = 1.0
    while transport is None:
        try:
            transport = yield fibra.net.connect(address)
        except socket.error:
            if retry is not None:
                retry -= 1
                if retry < 0:
                    raise 
            else:
                print 'Cannot connect to', address, 'retrying...'
                yield sleep
                sleep *= 1.5
                if sleep > 60:
                    sleep = 60

    yield fibra.Return(connection_class(transport))


