import http.server
import os
import sys
import logging

# Set up logging for health server
logging.basicConfig(
    level=logging.INFO,
    format="[HEALTH_SERVER] %(asctime)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("healthserver")

class _H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        # Suppress default HTTP server logging
        pass

try:
    # Azure App Service uses WEBSITES_PORT; fall back to 8000
    port = int(os.environ.get("WEBSITES_PORT", "8000"))
    logger.info(f"Starting health server on port {port}")

    server = http.server.HTTPServer(("0.0.0.0", port), _H)
    logger.info(f"Health server listening on 0.0.0.0:{port}")
    server.serve_forever()
except OSError as e:
    logger.error(f"Failed to start health server on port {port}: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Health server error: {e}", exc_info=True)
    sys.exit(1)
