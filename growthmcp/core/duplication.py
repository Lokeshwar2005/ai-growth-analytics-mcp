"""Native campaign duplication for GrowthMCP.

This module intentionally talks directly to Meta's Graph API. It does not
forward credentials or requests to any third-party hosted MCP service.
"""
import json
from typing import Optional

from .api import ensure_act_prefix, make_api_request, meta_api_tool
from .server import mcp_server


@mcp_server.tool()
@meta_api_tool
async def duplicate_campaign(
    campaign_id: str,
    new_name: Optional[str] = None,
    status_option: str = "PAUSED",
    deep_copy: bool = True,
    access_token: Optional[str] = None,
) -> str:
    """Duplicate a Meta campaign directly through the Graph API.

    The duplicate is created paused by default. This makes the operation safer
    for automation: the caller can inspect the returned object before enabling
    delivery.
    """
    if not campaign_id:
        return json.dumps({"error": "campaign_id is required"}, indent=2)
    if status_option not in {"ACTIVE", "PAUSED"}:
        return json.dumps({"error": "status_option must be ACTIVE or PAUSED"}, indent=2)

    endpoint = f"{campaign_id}/copies"
    params = {
        "deep_copy": str(bool(deep_copy)).lower(),
        "status_option": status_option,
    }
    if new_name:
        params["rename_options"] = json.dumps({"rename_prefix": new_name})

    data = await make_api_request(endpoint, access_token, params, method="POST")
    if isinstance(data, dict) and "error" in data:
        return json.dumps(data, indent=2)

    return json.dumps({
        "success": True,
        "source_campaign_id": ensure_act_prefix(campaign_id),
        "status_option": status_option,
        "deep_copy": deep_copy,
        "result": data,
    }, indent=2)
