import eel
import logging
import time

from contextlib import redirect_stdout
from io import StringIO
from threading import Thread, Lock
from time import sleep
from server import run_server
from http.client import HTTPConnection

server_lock = Lock()

logger = logging.getLogger(__name__)

def url_ok(url, port):

    try:
        conn = HTTPConnection(url, port)
        conn.request('GET', '/')
        r = conn.getresponse()
        return r.status == 200
    except:
        # logger.exception('Server not started')
        logger.debug("Not ready yet...")
        return False

if __name__ == '__main__':

    stream = StringIO()
    with redirect_stdout(stream):
        logger.debug('Starting server')
        t = Thread(target=run_server, args=(23947, False))
        t.daemon = True
        t.start()
        logger.debug('Checking server')

        while not url_ok('127.0.0.1', 23948):
            sleep(0.3)

        logger.debug('Server started')
        eel.init("static/eel")
        eel.start("bootstrap.html", block=True, port=23947)
