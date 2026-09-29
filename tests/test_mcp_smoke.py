"""Credential-free MCP protocol smoke test.

This test starts the real GrowthMCP stdio server and talks to it through
the MCP Python client. It intentionally does not call Meta APIs.
"""
import asyncio
import json
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

    # Validate registration on one clean MCP connection.
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=15)
            result = await asyncio.wait_for(session.list_tools(), timeout=15)

    tool_names = {tool.name for tool in result.tools}
    missing = EXPECTED_TOOLS - tool_names
    assert not missing, f"Expected MCP tools were not registered: {sorted(missing)}"
    assert len(tool_names) >= len(EXPECTED_TOOLS)

    # Keep both functional calls inside the same active MCP session.
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=15)

            tool_result = await asyncio.wait_for(
                session.call_tool(
                    "analyze_growth_query",
                    arguments={
                        "query": "What is ROAS?",
                        "records": [
                            {
                                "date": "2026-09-01",
                                "campaign_name": "Search",
                                "spend": 100,
                                "revenue": 250,
                            },
                            {
                                "date": "2026-09-02",
                                "campaign_name": "Search",
                                "spend": 50,
                                "revenue": 100,
                            },
                        ],
                        "source": "mcp-smoke-test",
                    },
                ),
                timeout=15,
            )

            assert not tool_result.isError
            assert tool_result.content
            payload = json.loads(tool_result.content[0].text)
            assert payload["record_count"] == 2
            assert payload["metrics_requested"] == ["roas"]
            assert payload["answer"]["metrics"]["roas"] == 350 / 150

            investigation_result = await asyncio.wait_for(
                session.call_tool(
                    "investigate_growth_issue",
                    arguments={
                        "question": "Why did ROAS drop?",
                        "current_records": [
                            {
                                "date": "2026-09-10",
                                "campaign_name": "Search",
                                "spend": 120,
                                "revenue": 80,
                            }
                        ],
                        "previous_records": [
                            {
                                "date": "2026-09-03",
                                "campaign_name": "Search",
                                "spend": 100,
                                "revenue": 100,
                            }
                        ],
                    },
                ),
                timeout=15,
            )

            assert not investigation_result.isError
            investigation = json.loads(investigation_result.content[0].text)
            assert investigation["issue_metric"] == "roas"
            assert investigation["target_change"]["change_pct"] == -33.333333333333336
            assert "revenue -20.0%" in investigation["summary"]
            assert "spend +20.0%" in investigation["summary"]
            assert {item["component"] for item in investigation["driver_decomposition"]} == {"revenue", "spend"}

            campaign_rows = investigation["breakdowns"]["campaign_name"]
            search = next(item for item in campaign_rows if item["value"] == "Search")
            assert search["current_record_count"] == 1
            assert search["previous_record_count"] == 1
            assert search["comparison"]["change_pct"] == -33.333333333333336
            assert investigation["investigation_notes"]["campaigns_added"] == []
            assert investigation["investigation_notes"]["campaigns_removed"] == []
