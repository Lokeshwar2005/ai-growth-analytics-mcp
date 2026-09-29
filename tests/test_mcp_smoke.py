"""Credential-free MCP protocol smoke test.

This test starts the real GrowthMCP stdio server and talks to it through
the MCP Python client. It intentionally does not call Meta APIs.
"""
import asyncio
import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


EXPECTED_TOOLS = {
    "get_ad_accounts",
    "get_campaigns",
    "get_insights",
    "calculate_growth_metrics",
    "analyze_growth_query",
    "investigate_campaign",
    "analyze_creatives",
    "analyze_cohorts",
    "build_evidence_packet",
    "investigate_growth_issue",
}


@pytest.mark.e2e
def test_stdio_mcp_server_initializes_and_lists_tools():
    asyncio.run(_smoke_test())


async def _smoke_test():
    env = os.environ.copy()
    env.pop("META_ACCESS_TOKEN", None)
    env.pop("META_APP_SECRET", None)
    env.pop("META_APP_ID", None)

    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "growthmcp"],
        env=env,
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=15)
            result = await asyncio.wait_for(session.list_tools(), timeout=15)

    tool_names = {tool.name for tool in result.tools}
    missing = EXPECTED_TOOLS - tool_names
    assert not missing, f"Expected MCP tools were not registered: {sorted(missing)}"
    assert len(tool_names) >= len(EXPECTED_TOOLS)
