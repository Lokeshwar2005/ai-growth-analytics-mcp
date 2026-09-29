"""Live Meta Ads -> GrowthMCP investigation bridge.

Read-only and opt-in: the operator supplies Meta credentials at runtime.
"""

import json
from datetime import date
from typing import Any, Dict, Optional

from .api import make_api_request
from .investigation import investigate_growth_issue
from .server import mcp_server


def _validate_range(value: Dict[str, str], name: str) -> Dict[str, str]:
    if not isinstance(value, dict) or "since" not in value or "until" not in value:
        raise ValueError(f"{name} must contain since and until in YYYY-MM-DD format")
    since = date.fromisoformat(value["since"])
    until = date.fromisoformat(value["until"])
    if since > until:
        raise ValueError(f"{name}.since must be on or before {name}.until")
    return {"since": since.isoformat(), "until": until.isoformat()}


def _rows(data: Any) -> list[dict]:
    if not isinstance(data, dict):
        raise ValueError("Meta API returned a non-object response")
    if data.get("error"):
        raise ValueError(str(data["error"]))
    rows = data.get("data")
    if not isinstance(rows, list):
        raise ValueError("Meta API response did not contain a data list")
    return [row for row in rows if isinstance(row, dict)]


@mcp_server.tool()
async def investigate_live_meta_growth_issue(
    question: str,
    account_id: str,
    current_time_range: Dict[str, str],
    previous_time_range: Dict[str, str],
    access_token: Optional[str] = None,
    level: str = "campaign",
    breakdown: str = "",
    limit: int = 100,
) -> str:
    """Fetch two Meta Insights periods and run the deterministic investigation engine."""
    if not account_id.strip():
        return json.dumps({"error": "account_id is required"}, indent=2)
    try:
        current_range = _validate_range(current_time_range, "current_time_range")
        previous_range = _validate_range(previous_time_range, "previous_time_range")
    except (TypeError, ValueError) as exc:
        return json.dumps({"error": str(exc)}, indent=2)

    account = account_id if account_id.startswith("act_") else f"act_{account_id}"
    endpoint = f"{account}/insights"
    fields = (
        "account_id,account_name,campaign_id,campaign_name,"
        "adset_id,adset_name,ad_id,ad_name,"
        "impressions,clicks,spend,actions,action_values,conversions"
    )
    params = {"fields": fields, "level": level, "limit": limit}
    if breakdown:
        params["breakdowns"] = breakdown

    try:
        current_data = await make_api_request(
            endpoint, access_token,
            {**params, "time_range": json.dumps(current_range)},
        )
        previous_data = await make_api_request(
            endpoint, access_token,
            {**params, "time_range": json.dumps(previous_range)},
        )
        current_rows = _rows(current_data)
        previous_rows = _rows(previous_data)

        result = json.loads(await investigate_growth_issue(
            question,
            current_records=current_rows,
            previous_records=previous_rows,
        ))
        result["source"] = "meta-live"
        result["meta_query"] = {
            "account_id": account,
            "level": level,
            "breakdown": breakdown,
            "current_time_range": current_range,
            "previous_time_range": previous_range,
            "current_rows": len(current_rows),
            "previous_rows": len(previous_rows),
        }
        result["limitations"].append(
            "Live Meta results depend on the account's attribution settings and available reporting data."
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({
            "error": "Live Meta investigation failed",
            "detail": str(exc),
            "source": "meta-live",
        }, indent=2)
