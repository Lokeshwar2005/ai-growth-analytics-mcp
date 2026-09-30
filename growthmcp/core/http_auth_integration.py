"""HTTP authentication integration for GrowthMCP."""
import contextvars, json
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from .utils import logger, redact_secret

_auth_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("growthmcp_auth_token", default=None)

class FastMCPAuthIntegration:
    @staticmethod
    def set_auth_token(token: str) -> None: _auth_token.set(token)
    @staticmethod
    def get_auth_token() -> Optional[str]: return _auth_token.get()
    @staticmethod
    def clear_auth_token() -> None: _auth_token.set(None)
    @staticmethod
    def extract_token_from_headers(headers: dict) -> Optional[str]:
        value = headers.get("Authorization") or headers.get("authorization")
        if value and value.lower().startswith("bearer "): return value[7:].strip()
        return headers.get("X-META-ACCESS-TOKEN") or headers.get("x-meta-access-token")

def patch_fastmcp_server(mcp_server) -> None:
    original_run = mcp_server.run
    def patched_run(transport="stdio", **kwargs):
        if transport == "streamable-http": setup_http_auth_patching()
        return original_run(transport=transport, **kwargs)
    mcp_server.run = patched_run

def setup_http_auth_patching() -> None:
    from . import api, auth, authentication
    original = auth.get_current_access_token
    async def get_current_access_token_with_http_support() -> Optional[str]:
        return FastMCPAuthIntegration.get_auth_token() or await original()
    auth.get_current_access_token = get_current_access_token_with_http_support
    api.get_current_access_token = get_current_access_token_with_http_support
    authentication.get_current_access_token = get_current_access_token_with_http_support

from starlette.middleware.cors import CORSMiddleware

def setup_starlette_middleware(app) -> None:
    if not app: return
    if not any(m.cls is CORSMiddleware for m in app.user_middleware):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id"],
        )
    if any(m.cls is AuthInjectionMiddleware for m in app.user_middleware): return
    app.add_middleware(AuthInjectionMiddleware)

def setup_fastmcp_http_auth(mcp_server) -> None:
    patch_fastmcp_server(mcp_server)
    for name in ("streamable_http_app", "sse_app"):
        provider = getattr(mcp_server, name, None)
        if not callable(provider): continue
        def patched(*args, _provider=provider, **kwargs):
            app = _provider(*args, **kwargs); setup_starlette_middleware(app); return app
        setattr(mcp_server, name, patched)

class AuthInjectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        token = FastMCPAuthIntegration.extract_token_from_headers(dict(request.headers))
        if token:
            logger.debug("GrowthMCP auth token: %s", redact_secret(token))
            FastMCPAuthIntegration.set_auth_token(token)
            try: return await call_next(request)
            finally: FastMCPAuthIntegration.clear_auth_token()
        return await call_next(request)

fastmcp_auth = FastMCPAuthIntegration()
