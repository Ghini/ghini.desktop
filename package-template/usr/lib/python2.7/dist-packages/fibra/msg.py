import fibra
import fibra.net
import fibra.event

import cPickle as pickle
import exceptions
import json
import time
import types
import zlib


schedule = fibra.schedule()

class NULL(object): pass

class Timeout(Exception): pass

class Disconnect(Exception): pass


class Connection(fibra.event.Connection):

    COMPRESSION_THRESHOLD = 1024
    REQUEST_TIMEOUT = 10.0

    def __init__(self, *args, **kw):
        fibra.event.Connection.__init__(self, *args, **kw)
        self.request_id = 0
        self.requests = {}
        schedule.install(self.check_timeouts())
        self.rpc = None
    
    def check_timeouts(self):
        while self.running:
            now = time.time()
            for request_id, (T, task) in self.requests.items():
                if now - T > self.REQUEST_TIMEOUT:
                    self.requests.pop(request_id)
                    schedule.install(task, Timeout(self.protocol.transport.address))
            yield 0.25

    def serialize(self, response, obj, headers={}):
        if 'accept' in headers:
            if headers['accept'] == 'text/json':
                response['content-type'] = 'text/json' 
                body = json.dumps(obj)
        else:
            response['content-type'] = 'text/pickle' 
            body = pickle.dumps(obj)
        if len(body) > self.COMPRESSION_THRESHOLD:
            body = zlib.compress(body)
            response['compression'] = 'zlib'
        return body

    def deserialize(self, headers, body):
        if headers.get('compression', None) == 'zlib':
            body = zlib.decompress(body)
        content_type = headers.get('content-type', None)
        if content_type == 'text/pickle':
            body = pickle.loads(body)
        elif content_type == 'text/json':
            body = json.loads(body)
        return body
            
    def request(self, name, args, kw):
        headers = {}
        body = args, kw
        request_id = headers["request-id"] = str(self.request_id)
        headers['method'] = name
        self.request_id += 1
        task = yield fibra.Self()
        self.requests[request_id] = time.time(), task
        yield self.send('request', headers, body)
        response = yield fibra.Suspend()
        yield fibra.Return(response)
    
    def dispatch(self, top, headers, body):
        if body:
            body = self.deserialize(headers, body)
        yield fibra.event.Connection.dispatch(self, top, headers, body)

    def do_request(self, headers, body):
        response = {}
        response['request-id'] = headers['request-id']
        result = NULL
        try:
            if headers["method"][0] == "_": raise AttributeError('cannot access private methods.')
            method = getattr(self.rpc, headers['method'])
        except AttributeError, e:
            response['exception'] = 'AttributeError'
            response['msg'] = str(e)
        else:
            args, kw = body
            try:
                result = method(*args, **kw)
                while type(result) is types.GeneratorType:
                    result = yield result
                result = self.serialize(response, result, headers)
            except Exception, e:
                response['exception'] = e.__class__.__name__
                response['msg'] = str(e)
                result = NULL
        yield self.send('response', response, result)

    def send(self, top, response, body=NULL):
        if body is NULL:
            body = ""
        elif 'content-type' not in response:
            body = self.serialize(response, body)
        try:
            yield fibra.event.Connection.send(self, top, response, body)
        except fibra.ClosedTube:
            raise Disconnect()
    
    def do_response(self, headers, body):
        request_id = headers["request-id"]
        if request_id in self.requests:
            T, task = self.requests.pop(request_id)
            if "exception" in headers:
                schedule.install(task, getattr(exceptions, headers['exception'])(headers['msg']))
            else:
                schedule.install(task, body)
            yield None
        else:
            print "Expired request:", request_id


class RPC(object):
    def __init__(self, connection):
        self.connection = connection

    def __getattr__(self, key):
        return lambda *args, **kw: self.connection.request(key, args, kw)

