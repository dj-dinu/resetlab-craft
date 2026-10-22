"""Threaded HTTP server for the app's numeric loopback listeners."""
from http.server import ThreadingHTTPServer
from socketserver import TCPServer


class LoopbackHTTPServer(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer normally resolves the bound address with getfqdn(). The
        # app only uses numeric loopback addresses and does not need a DNS name.
        TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]
