"""Local OAuth callback server for GrowthMCP."""
import os, secrets, socket, threading, time
from html import escape as html_escape
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import parse_qs, urlparse
from .utils import logger, redact_secret

token_container = {"token": None, "expires_in": None, "user_id": None, "auth_code": None}
callback_server_thread = None
callback_server_lock = threading.Lock()
callback_server_running = False
callback_server_port = None
callback_server_instance = None
server_shutdown_timer = None
CALLBACK_SERVER_TIMEOUT = 180
_oauth_state = None
_oauth_state_lock = threading.Lock()
CALLBACK_SERVER_HOST = "127.0.0.1"
MAX_ERROR_DISPLAY_LENGTH = 200

def new_oauth_state() -> str:
    global _oauth_state
    with _oauth_state_lock:
        _oauth_state = secrets.token_urlsafe(32)
        return _oauth_state
def get_oauth_state() -> Optional[str]:
    with _oauth_state_lock: return _oauth_state
def consume_oauth_state(received: Optional[str]) -> bool:
    global _oauth_state
    with _oauth_state_lock:
        if not _oauth_state or not received or not secrets.compare_digest(_oauth_state, received): return False
        _oauth_state = None; return True

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path.startswith("/callback"): self._handle_oauth_callback()
            else: self.send_response(404); self.end_headers()
        except Exception:
            self.send_response(500); self.end_headers()
    def _send_html(self, html: str, csp: str = "default-src 'none'"):
        body = html.encode()
        self.send_response(200)
        for k,v in {
            "Content-type":"text/html; charset=utf-8","Content-Length":str(len(body)),
            "Content-Security-Policy":csp,"X-Content-Type-Options":"nosniff",
            "X-Frame-Options":"DENY","Referrer-Policy":"no-referrer","Cache-Control":"no-store"
        }.items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)
    def _handle_oauth_callback(self):
        p = parse_qs(urlparse(self.path).query)
        code, state, error = p.get("code",[None])[0], p.get("state",[None])[0], p.get("error",[None])[0]
        csp = "default-src 'none'"
        if error:
            safe = html_escape(error[:MAX_ERROR_DISPLAY_LENGTH])
            html = f"<html><body><h1>Authorization Failed</h1><p>{safe}</p><p>Close this window.</p></body></html>"
        elif code and not consume_oauth_state(state):
            html = "<html><body><h1>Authorization Rejected</h1><p>State validation failed. Close this window and start again.</p></body></html>"
            logger.warning("GrowthMCP OAuth callback rejected due to invalid state")
        elif code:
            logger.info("Received authorization code: %s", redact_secret(code))
            token_container.update({"auth_code":code,"state":state,"timestamp":time.monotonic()})
            threading.Timer(1.0, shutdown_callback_server).start()
            nonce = secrets.token_urlsafe(16)
            csp = f"default-src 'none'; script-src 'nonce-{nonce}'"
            html = f"<html><body><h1>Authorization Successful</h1><p>GrowthMCP authorization completed.</p><script nonce='{nonce}'>setTimeout(function(){{window.close();}},2000);</script></body></html>"
        else:
            html = "<html><body><h1>Unexpected Response</h1><p>No authorization code or error received.</p></body></html>"
        self._send_html(html, csp)
    def log_message(self, format, *args): return

def shutdown_callback_server():
    global callback_server_running, callback_server_thread, callback_server_port, callback_server_instance, server_shutdown_timer
    with callback_server_lock:
        if not callback_server_running: return
        if server_shutdown_timer: server_shutdown_timer.cancel(); server_shutdown_timer=None
        try:
            if callback_server_instance:
                callback_server_instance.shutdown(); callback_server_instance.server_close()
            if callback_server_thread and callback_server_thread.is_alive():
                callback_server_thread.join(timeout=5)
        finally:
            callback_server_running=False; callback_server_thread=None; callback_server_port=None; callback_server_instance=None

def start_callback_server() -> int:
    global callback_server_thread, callback_server_running, callback_server_port, callback_server_instance, server_shutdown_timer
    if os.environ.get("GROWTHMCP_DISABLE_CALLBACK_SERVER"):
        raise RuntimeError("Callback server is disabled via GROWTHMCP_DISABLE_CALLBACK_SERVER")
    with callback_server_lock:
        if callback_server_running: return callback_server_port
        port = 8080
        for _ in range(10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: s.bind((CALLBACK_SERVER_HOST,port))
                break
            except OSError: port += 1
        else: raise RuntimeError("Could not find an available callback port")
        callback_server_port = port
        new_oauth_state()
        callback_server_thread = threading.Thread(target=server_thread, daemon=True)
        callback_server_thread.start(); time.sleep(0.25)
        if not callback_server_running: raise RuntimeError("Failed to start callback server")
        server_shutdown_timer = threading.Timer(CALLBACK_SERVER_TIMEOUT, shutdown_callback_server)
        server_shutdown_timer.start()
        return port

def server_thread():
    global callback_server_running, callback_server_instance
    try:
        callback_server_instance = HTTPServer((CALLBACK_SERVER_HOST, callback_server_port), CallbackHandler)
        callback_server_running = True
        callback_server_instance.serve_forever()
    finally:
        callback_server_running = False
