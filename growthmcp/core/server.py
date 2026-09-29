"""GrowthMCP MCP server configuration."""
from mcp.server.fastmcp import FastMCP
import argparse, os
from .auth import login as login_auth
from .utils import logger

mcp_server = FastMCP("growthmcp")

def login_cli() -> None:
    logger.info("Starting GrowthMCP Meta authentication flow")
    login_auth()

def main() -> int:
    parser = argparse.ArgumentParser(description="GrowthMCP - Model Context Protocol server for Meta Ads",epilog="https://github.com/Lokeshwar2005/ai-growth-analytics-mcp")
    parser.add_argument("--login",action="store_true")
    parser.add_argument("--app-id",type=str)
    parser.add_argument("--version",action="store_true")
    parser.add_argument("--transport",choices=["stdio","streamable-http"],default="stdio")
    parser.add_argument("--port",type=int,default=8080)
    parser.add_argument("--host",type=str,default="127.0.0.1")
    parser.add_argument("--sse-response",action="store_true")
    args=parser.parse_args()
    from .auth import auth_manager, meta_config
    if args.app_id: auth_manager.app_id=args.app_id; meta_config.set_app_id(args.app_id)
    elif os.environ.get("META_APP_ID"): auth_manager.app_id=os.environ["META_APP_ID"]; meta_config.set_app_id(os.environ["META_APP_ID"])
    if args.version:
        from growthmcp import __version__; print(f"GrowthMCP v{__version__}"); return 0
    if args.login: login_cli(); return 0
    from . import accounts,campaigns,adsets,ads,insights,authentication,ads_library,budget_schedules,reports
    if args.transport=="streamable-http":
        mcp_server.settings.host=args.host; mcp_server.settings.port=args.port
        mcp_server.settings.stateless_http=True; mcp_server.settings.json_response=not args.sse_response
        from .http_auth_integration import setup_fastmcp_http_auth
        setup_fastmcp_http_auth(mcp_server)
        logger.info("Starting GrowthMCP Streamable HTTP on %s:%s",args.host,args.port)
        mcp_server.run(transport="streamable-http")
    else:
        logger.info("Starting GrowthMCP over stdio"); mcp_server.run(transport="stdio")
    return 0

if __name__=="__main__": raise SystemExit(main())
