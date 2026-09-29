"""Authentication MCP tools for GrowthMCP."""
import json, os
from typing import Optional
from .auth import start_callback_server, auth_manager
from .server import mcp_server
from .utils import logger, redact_secret, META_APP_SECRET

ENABLE_LOGIN_LINK = not bool(os.environ.get("GROWTHMCP_DISABLE_LOGIN_LINK",""))

async def get_login_link(access_token: Optional[str]=None) -> str:
    if os.environ.get("GROWTHMCP_DISABLE_CALLBACK_SERVER"):
        return json.dumps({"message":"Local OAuth is disabled.","option":"Set META_ACCESS_TOKEN or enable the local callback server."}, indent=2)
    cached = auth_manager.get_access_token()
    if cached and not access_token:
        return json.dumps({"message":"Already authenticated with Meta Ads.","token_info":redact_secret(cached),"authentication_method":"meta_oauth"}, indent=2)
    try:
        port = start_callback_server()
        auth_manager.redirect_uri = f"http://localhost:{port}/callback"
        login_url = auth_manager.get_auth_url()
    except Exception as exc:
        logger.error("Could not start local OAuth: %s", exc)
        return json.dumps({"message":"Local Authentication Unavailable","error":str(exc),"solution":"Set META_ACCESS_TOKEN or configure META_APP_ID and META_APP_SECRET for your own Meta app."}, indent=2)
    if not login_url:
        return json.dumps({"message":"META_APP_ID is not configured.","solution":"Set META_APP_ID for your own Meta developer application."}, indent=2)
    return json.dumps({
        "message":"Click to authenticate with Meta Ads","login_url":login_url,
        "instructions":"Complete the Meta OAuth flow in your browser. The token is stored in the local GrowthMCP cache.",
        "token_exchange":bool(META_APP_SECRET),"authentication_method":"meta_oauth"
    }, indent=2)

if ENABLE_LOGIN_LINK: get_login_link = mcp_server.tool()(get_login_link)
