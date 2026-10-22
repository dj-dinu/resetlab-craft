"""Loopback serving and shutdown must not depend on a hostname lookup."""
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler
import json
import socket
import threading
import unittest
from unittest.mock import patch

from music_library_lab.desktop import LocalSession
from music_library_lab.server import LoopbackHTTPServer


class LoopbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"loopback"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class LoopbackServerTests(unittest.TestCase):
    def assert_closed(self, port):
        with socket.socket() as probe:
            probe.settimeout(2)
            self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0)

    def test_server_serves_and_closes_without_reverse_dns(self):
        with patch("socket.getfqdn", side_effect=AssertionError("Unexpected hostname lookup")) as lookup:
            server = LoopbackHTTPServer(("127.0.0.1", 0), LoopbackHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
                self.assertEqual(server.server_name, "localhost")
                self.assertEqual(server.server_port, server.server_address[1])
                self.assertGreater(server.server_port, 0)
                thread.start()
                connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                try:
                    connection.request("GET", "/")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b"loopback")
                finally:
                    connection.close()
            finally:
                if thread.is_alive():
                    server.shutdown()
                server.server_close()
                thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assert_closed(server.server_port)
            lookup.assert_not_called()

    def test_desktop_session_serves_and_stops_without_reverse_dns(self):
        with patch("socket.getfqdn", side_effect=AssertionError("Unexpected hostname lookup")) as lookup:
            session = LocalSession()
            try:
                self.assertIsInstance(session.server, LoopbackHTTPServer)
                self.assertEqual(session.server.server_address[0], "127.0.0.1")
                session.start()
                connection = HTTPConnection("127.0.0.1", session.server.server_port, timeout=5)
                try:
                    connection.request("GET", "/api/config", headers={"X-Local-Token": session.state.token})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertFalse(json.loads(response.read())["manager_enabled"])
                finally:
                    connection.close()
            finally:
                session.stop()
            self.assertTrue(session.closed)
            self.assertFalse(session.thread.is_alive())
            self.assert_closed(session.server.server_port)
            lookup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
