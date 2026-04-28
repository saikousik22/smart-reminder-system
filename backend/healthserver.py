import http.server
import os

class _H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *a):
        pass

port = int(os.environ.get("WEBSITES_PORT", 8000))
http.server.HTTPServer(("", port), _H).serve_forever()
