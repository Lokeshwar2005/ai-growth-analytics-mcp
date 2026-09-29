"""Opt-in live Meta Graph API smoke test.

This test never runs against Meta unless the operator explicitly supplies:
- GROWTHMCP_LIVE_META_TEST=1
- META_ACCESS_TOKEN
- GROWTHMCP_META_ACCOUNT_ID

No credentials are stored in the repository or sent to CI.
"""
import json
import os

import pytest

from growthmcp.core.api import make_api_request
from growthmcp.core.analyst import analyze_growth_query
from growthmcp.core.workflows import normalize_growth_records


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_meta_account_insights_round_trip():
    if os.getenv("GROWTHMCP_LIVE_META_TEST") != "1":
        pytest.skip("Opt-in only: set GROWTHMCP_LIVE_META_TEST=1 to call Meta.")
    token = os.getenv("META_ACCESS_TOKEN")
    account_id = os.getenv("GROWTHMCP_META_ACCOUNT_ID")
    if not token or not account_id:
        pytest.skip("Requires META_ACCESS_TOKEN and GROWTHMCP_META_ACCOUNT_ID.")

    account = account_id if account_id.startswith("act_") else f"act_{account_id}"
    data = await make_api_request(
        f"{account}/insights",
        token,
        {
            "fields": "account_id,account_name,campaign_id,campaign_name,spend,impressions,clicks",
            "level": "campaign",
            "date_preset": "last_7d",
            "limit": 100,
        },
    )

    assert "error" not in data, json.dumps(data, indent=2)
    assert isinstance(data.get("data"), list)
    assert data.get("data"), "Meta returned no campaign insight rows for last_7d."

    normalized = await normalize_growth_records(data["data"], source="meta-live")
    assert normalized["record_count"] == len(data["data"])
    assert normalized["records"]

    analysis = await analyze_growth_query(
        query="What is spend?",
        records=normalized["records"],
        source="meta-live-smoke",
    )
    payload = json.loads(analysis)
    assert payload["record_count"] == len(data["data"])
    assert "spend" in payload["metrics_requested"]
