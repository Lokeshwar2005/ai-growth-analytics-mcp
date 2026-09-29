"""Authentication helpers for GrowthMCP."""
from typing import Any, Dict, Optional
import json, os, pathlib, platform, time, webbrowser
import requests

from .callback_server import (
    start_callback_server, token_container, get_oauth_state, new_oauth_state
)
from .utils import logger, redact_secret, restrict_permissions

AUTH_SCOPE = "business_management,public_profile,pages_show_list,pages_read_engagement"
AUTH_REDIRECT_URI = "http://localhost:8080/callback"
AUTH_RESPONSE_TYPE = "code"
DISABLE_CALLBACK_ENV = "GROWTHMCP_DISABLE_CALLBACK_SERVER"
needs_authentication = False

class MetaConfig:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.app_id = os.environ.get("META_APP_ID", "")
        return cls._instance
    def set_app_id(self, app_id: str) -> None:
        self.app_id = app_id or ""
        os.environ["META_APP_ID"] = self.app_id
    def get_app_id(self) -> str:
        return getattr(self, "app_id", "") or os.environ.get("META_APP_ID", "")
    def is_configured(self) -> bool:
        return bool(self.get_app_id())

meta_config = MetaConfig()

class TokenInfo:
    def __init__(self, access_token: str, expires_in: Optional[int] = None, user_id: Optional[str] = None):
        self.access_token, self.expires_in, self.user_id = access_token, expires_in, user_id
        self.created_at = int(time.time())
    def is_expired(self) -> bool:
        return bool(self.expires_in) and int(time.time()) > self.created_at + self.expires_in
    def serialize(self) -> Dict[str, Any]:
        return {"access_token": self.access_token, "expires_in": self.expires_in, "user_id": self.user_id, "created_at": self.created_at}
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "TokenInfo":
        t = cls(data.get("access_token",""), data.get("expires_in"), data.get("user_id"))
        t.created_at = data.get("created_at", int(time.time()))
        return t

TOKEN_CACHE_FILE_MODE, TOKEN_CACHE_DIR_MODE = 0o600, 0o700

class AuthManager:
    def __init__(self, app_id: str, redirect_uri: str = AUTH_REDIRECT_URI):
        self.app_id, self.redirect_uri, self.token_info = app_id or "", redirect_uri, None
        self._load_cached_token()
    def _get_token_cache_path(self) -> pathlib.Path:
        if platform.system() == "Windows":
            base = pathlib.Path(os.environ.get("APPDATA", str(pathlib.Path.home())))
        elif platform.system() == "Darwin":
            base = pathlib.Path.home() / "Library" / "Application Support"
        else:
            base = pathlib.Path.home() / ".config"
        d = base / "growthmcp"
        d.mkdir(parents=True, exist_ok=True, mode=TOKEN_CACHE_DIR_MODE)
        restrict_permissions(d, TOKEN_CACHE_DIR_MODE)
        return d / "token_cache.json"
    def _load_cached_token(self) -> bool:
        p = self._get_token_cache_path()
        if not p.exists(): return False
        try:
            restrict_permissions(p, TOKEN_CACHE_FILE_MODE)
            data = json.loads(p.read_text())
            t = TokenInfo.deserialize(data)
            if not t.access_token or t.is_expired() or int(time.time()) - t.created_at > 60*24*3600:
                p.unlink(missing_ok=True); return False
            self.token_info = t; return True
        except Exception:
            try: p.unlink(missing_ok=True)
            except OSError: pass
            return False
    def _save_token_to_cache(self) -> None:
        if not self.token_info: return
        p = self._get_token_cache_path()
        fd = os.open(p, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, TOKEN_CACHE_FILE_MODE)
        with os.fdopen(fd, "w") as f: json.dump(self.token_info.serialize(), f)
        restrict_permissions(p, TOKEN_CACHE_FILE_MODE)
    def get_auth_url(self) -> str:
        app_id = self.app_id or meta_config.get_app_id()
        if not app_id: return ""
        from urllib.parse import urlencode
        state = get_oauth_state() or new_oauth_state()
        return "https://www.facebook.com/v24.0/dialog/oauth?" + urlencode({
            "client_id": app_id, "redirect_uri": self.redirect_uri, "scope": AUTH_SCOPE,
            "response_type": AUTH_RESPONSE_TYPE, "state": state,
        })
    def get_access_token(self) -> Optional[str]:
        return self.token_info.access_token if self.token_info and not self.token_info.is_expired() else None
    def invalidate_token(self) -> None:
        global needs_authentication
        needs_authentication, self.token_info = True, None
        try: self._get_token_cache_path().unlink(missing_ok=True)
        except OSError: pass
    clear_token = invalidate_token

def exchange_code_for_token(code: str) -> Optional[TokenInfo]:
    app_id, app_secret = meta_config.get_app_id(), os.environ.get("META_APP_SECRET","")
    if not app_id or not app_secret:
        logger.error("META_APP_ID and META_APP_SECRET are required for OAuth code exchange")
        return None
    try:
        r = requests.get("https://graph.facebook.com/v24.0/oauth/access_token", params={
            "client_id": app_id, "client_secret": app_secret,
            "redirect_uri": auth_manager.redirect_uri, "code": code
        }, timeout=30)
        r.raise_for_status()
        data = r.json()
        token = data.get("access_token")
        return TokenInfo(token, data.get("expires_in")) if token else None
    except Exception as exc:
        logger.error("OAuth code exchange failed: %s", exc)
        return None

def process_token_response(container: Dict[str, Any]) -> bool:
    global needs_authentication
    code, token = container.get("auth_code"), container.get("token")
    token_info = TokenInfo(token, container.get("expires_in"), container.get("user_id")) if token else exchange_code_for_token(code) if code else None
    if not token_info:
        needs_authentication = True; return False
    auth_manager.token_info = token_info
    auth_manager._save_token_to_cache()
    needs_authentication = False
    return True

async def get_current_access_token() -> Optional[str]:
    token = os.environ.get("META_ACCESS_TOKEN")
    if token:
        return token if len(token) >= 20 else None
    token = auth_manager.get_access_token()
    return token if token and len(token) >= 20 else None

def login() -> None:
    print("Starting GrowthMCP Meta authentication flow...")
    try:
        port = start_callback_server()
        auth_manager.redirect_uri = f"http://localhost:{port}/callback"
        url = auth_manager.get_auth_url()
        if not url:
            print("META_APP_ID is not configured. Set it to your own Meta developer app ID.")
            return
        print(f"Open this URL to authenticate with Meta:\n{url}")
        webbrowser.open(url)
        for _ in range(150):
            time.sleep(2)
            if token_container.get("auth_code") or token_container.get("token"):
                print("Authentication successful." if process_token_response(token_container) else "Token exchange failed.")
                return
        print("Authentication timed out. Please try again.")
    except Exception as exc:
        print(f"Authentication failed: {exc}")

META_APP_ID = os.environ.get("META_APP_ID", "")
auth_manager = AuthManager(META_APP_ID)
