import queue
import socket
from threading import Thread, Event, Lock

from . import bencode
from .log import log
from . import sessions


class Session():
    handlers = dict()
    errors = dict()

    def __init__(self, id, client):
        self.id = id
        self.client = client
        self.op_count = 0
        self.lock = Lock()

    def op_id(self):
        with self.lock:
            self.op_count += 1

        return self.op_count

    def op(self, d):
        d['session'] = self.id
        d['id'] = self.op_id()
        d['nrepl.middleware.caught/print?'] = 'true'
        d['nrepl.middleware.print/stream?'] = 'true'
        return d

    def output(self, x):
        self.client.recvq.put(x)

    def send(self, op, handler=None):
        op = self.op(op)

        if not handler:
            handler = self.client.recvq.put

        self.handlers[op['id']] = handler
        self.client.sendq.put(op)

    def handle(self, response):
        id = response.get('id')
        handler = self.handlers.get(id, self.client.recvq.put)

        try:
            handler.__call__(response)
        finally:
            if response.get('status') == ['done']:
                self.handlers.pop(id, None)
                self.errors.pop(id, None)

    def denounce(self, response):
        id = response.get('id')

        if id:
            self.errors[id] = response

    def is_denounced(self, response):
        return response.get('id') in self.errors

    def terminate(self):
        self.client.halt()


class Client(object):
    '''
    Here's how Client works:

    1. Open a socket connection to the given host and port.
    2. Start a worker that gets items from a queue and sends them over the
       socket for evaluation.
    3. Start a worker that reads bencode strings from the socket,
       parses them, and puts them into a queue.

    Calling `halt()` on a Client will stop the background threads and close
    the socket connection. Client is a context manager, so you can use it
    with the `with` statement.
    '''

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.buffer = self.socket.makefile(mode='rwb')

        log.debug({
            'event': 'socket/connect',
            'host': self.host,
            'port': self.port
        })

        return self

    def disconnect(self):
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
                log.debug({'event': 'socket/disconnect'})
            except OSError as e:
                log.debug({'event': 'error', 'exception': e})

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sendq = queue.Queue()
        self.recvq = queue.Queue()
        self.stop_event = Event()

    def clone_session(self):
        self.sendq.put({'op': 'clone'})
        id = self.recvq.get().get('new-session')
        return Session(id, self)

    def go(self):
        self.connect()

        send_loop = Thread(daemon=True, target=self.send_loop)
        send_loop.name = 'tutkain.client.send_loop'
        send_loop.start()

        recv_loop = Thread(daemon=True, target=self.recv_loop)
        recv_loop.name = 'tutkain.client.recv_loop'
        recv_loop.start()

        return self

    def __enter__(self):
        self.go()
        return self

    def send_loop(self):
        while True:
            item = self.sendq.get()

            if item is None:
                break

            log.debug({'event': 'socket/send', 'item': item})

            bencode.write(self.buffer, item)

        log.debug({'event': 'thread/exit'})

    def handle(self, response):
        id = response.get('session')
        session = sessions.get_by_id(id)

        if session:
            session.handle(response)
        else:
            self.recvq.put(response)

    def recv_loop(self):
        try:
            while not self.stop_event.is_set():
                item = bencode.read(self.buffer)

                # nREPL session closed, break loop
                if item.get('status') == ['done', 'session-closed']:
                    break

                log.debug({'event': 'socket/recv', 'item': item})
                self.handle(item)
        except OSError as e:
            log.error({
                'event': 'error',
                'exception': e
            })
        finally:
            # If we receive a stop event, put a None into the queue to tell
            # consumers to stop reading it.
            self.recvq.put(None)

            log.debug({'event': 'thread/exit'})

            # We've exited the loop that reads from the socket, so we can
            # close the connection to the socket.
            self.disconnect()

    def halt(self):
        # Close nREPL session
        self.sendq.put({'op': 'close'})

        # Feed poison pill to input queue.
        self.sendq.put(None)

        # Trigger the kill switch to tell background threads to stop reading
        # from the socket.
        self.stop_event.set()

    def __exit__(self, type, value, traceback):
        self.halt()
