#!/usr/bin/env python3
"""Verify full, suffix, open-ended, invalid and HEAD range requests."""
import functools
import http.client
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serve import RangeHandler


class QuietHandler(RangeHandler):
    def log_message(self, fmt, *args):
        pass


class ServerTests(unittest.TestCase):
    def test_byte_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'test.jar').write_bytes(b'0123456789')
            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=directory))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                for request, status, expected, span in [
                    (None, 200, b'0123456789', None),
                    ('bytes=2-4', 206, b'234', 'bytes 2-4/10'),
                    ('bytes=5-', 206, b'56789', 'bytes 5-9/10'),
                    ('bytes=-3', 206, b'789', 'bytes 7-9/10'),
                    ('bytes=0-9999', 206, b'0123456789', 'bytes 0-9/10'),
                    ('bytes=10-', 416, b'', 'bytes */10'),
                    ('bytes=-0', 416, b'', 'bytes */10'),
                    ('bytes=3-2', 416, b'', 'bytes */10'),
                    ('bytes=', 416, b'', 'bytes */10'),
                ]:
                    connection = http.client.HTTPConnection(*server.server_address)
                    connection.request('GET', '/test.jar', headers={'Range': request} if request else {})
                    response = connection.getresponse()
                    self.assertEqual(response.status, status, request)
                    self.assertEqual(response.getheader('Content-Range'), span)
                    self.assertEqual(response.getheader('Accept-Ranges'), 'bytes')
                    self.assertEqual(response.read(), expected)
                    connection.close()
                connection = http.client.HTTPConnection(*server.server_address)
                connection.request('HEAD', '/test.jar', headers={'Range': 'bytes=1-3'})
                response = connection.getresponse()
                self.assertEqual(response.status, 206)
                self.assertEqual(response.getheader('Content-Length'), '3')
                self.assertEqual(response.read(), b'')
                connection.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main()
