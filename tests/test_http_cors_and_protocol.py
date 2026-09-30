"""Tests for Streamable HTTP CORS, protocol handling, and authentication integration."""
import pytest
from starlette.testclient import TestClient
from growthmcp.core.server import mcp_server
from growthmcp.core.http_auth_integration import setup_fastmcp_http_auth

def test_streamable_http_cors_and_protocol_lifecycle():
    # Reset session manager if previously initialized
    mcp_server._session_manager = None
    setup_fastmcp_http_auth(mcp_server)
    app = mcp_server.streamable_http_app()

    with TestClient(app, base_url="http://127.0.0.1:8080") as client:
        # 1. CORS Preflight OPTIONS
        preflight_res = client.options("/mcp", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "mcp-session-id,content-type"
        })
        assert preflight_res.status_code == 200
        assert preflight_res.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert "POST" in preflight_res.headers.get("access-control-allow-methods", "")

        # 2. Initialize handshake
        init_res = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-dashboard", "version": "1.0.0"}
            }
        }, headers={
            "Origin": "http://localhost:5173",
            "Accept": "application/json, text/event-stream"
        })
        assert init_res.status_code == 200
        # Verify CORS expose headers on POST response
        assert "mcp-session-id" in init_res.headers.get("access-control-expose-headers", "").lower()
        session_id = init_res.headers.get("mcp-session-id")
        assert session_id is not None
        assert "event: message" in init_res.text
        assert "serverInfo" in init_res.text

        # 3. Initialized notification
        notif_res = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }, headers={
            "Origin": "http://localhost:5173",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": session_id
        })
        assert notif_res.status_code in (200, 202)

        # 4. List tools
        tools_res = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }, headers={
            "Origin": "http://localhost:5173",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": session_id
        })
        assert tools_res.status_code == 200
        assert "calculate_growth_metrics" in tools_res.text
        assert "get_ad_accounts" in tools_res.text
        assert "investigate_live_meta_growth_issue" in tools_res.text
