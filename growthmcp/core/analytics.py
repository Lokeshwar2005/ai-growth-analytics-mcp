"""Platform-neutral growth analytics tools.

These tools operate on metric records supplied by an MCP client or another
GrowthMCP tool. They keep the analytics layer independent from the Meta API so
it can later consume Google Ads, TikTok, CRM, or product-event data as well.
"""
import json
import statistics
from typing import Any, Dict, List, Optional

from .server import mcp_server


def _num(row: Dict[str, Any], key: str) -> float:
    try:
        value = row.get(key, 0)
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _metrics(row: Dict[str, Any]) -> Dict[str, float]:
    spend = _num(row, "spend")
    impressions = _num(row, "impressions")
    clicks = _num(row, "clicks")
    conversions = _num(row, "conversions")
    leads = _num(row, "leads")
    revenue = _num(row, "revenue")
    return {
        "spend": spend,
        "revenue": revenue,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "leads": leads,
        "ctr": (clicks / impressions * 100) if impressions else 0.0,
        "cpc": (spend / clicks) if clicks else 0.0,
        "cpa": (spend / conversions) if conversions else 0.0,
        "cpl": (spend / leads) if leads else 0.0,
        "conversion_rate": (conversions / clicks * 100) if clicks else 0.0,
        "roas": (revenue / spend) if spend else 0.0,
    }


@mcp_server.tool()
async def calculate_growth_metrics(records: List[Dict[str, Any]]) -> str:
    """Calculate CTR, CPC, CPA, CPL, conversion rate, and ROAS for records."""
    if not isinstance(records, list):
        return json.dumps({"error": "records must be a list of objects"}, indent=2)
    output = []
    for row in records:
        if not isinstance(row, dict):
            continue
        result = dict(row)
        result.update(_metrics(row))
        output.append(result)
    totals = _metrics({
        key: sum(_num(r, key) for r in records if isinstance(r, dict))
        for key in ("spend", "revenue", "impressions", "clicks", "conversions", "leads")
    })
    return json.dumps({"records": output, "totals": totals}, indent=2)


@mcp_server.tool()
async def compare_campaign_metrics(campaigns: List[Dict[str, Any]], metric: str = "roas") -> str:
    """Compare campaign metric values without ranking or recommending a campaign."""
    allowed = {"spend", "revenue", "impressions", "clicks", "conversions", "leads", "ctr", "cpc", "cpa", "cpl", "conversion_rate", "roas"}
    if metric not in allowed:
        return json.dumps({"error": f"metric must be one of: {', '.join(sorted(allowed))}"}, indent=2)
    rows = []
    for row in campaigns:
        if not isinstance(row, dict):
            continue
        m = _metrics(row)
        rows.append({"campaign_id": row.get("campaign_id"), "campaign_name": row.get("campaign_name"), metric: m[metric]})
    return json.dumps({"metric": metric, "campaigns": rows}, indent=2)


@mcp_server.tool()
async def detect_metric_anomalies(values: List[float], z_threshold: float = 2.0) -> str:
    """Flag unusually high/low observations using a z-score threshold."""
    if len(values) < 3:
        return json.dumps({"error": "At least 3 numeric observations are required"}, indent=2)
    try:
        nums = [float(v) for v in values]
    except (TypeError, ValueError):
        return json.dumps({"error": "values must contain only numbers"}, indent=2)
    mean = statistics.mean(nums)
    stdev = statistics.pstdev(nums)
    if stdev == 0:
        return json.dumps({"mean": mean, "stddev": 0.0, "anomalies": []}, indent=2)
    anomalies = []
    for i, value in enumerate(nums):
        z = (value - mean) / stdev
        if abs(z) >= z_threshold:
            anomalies.append({"index": i, "value": value, "z_score": z})
    return json.dumps({"mean": mean, "stddev": stdev, "z_threshold": z_threshold, "anomalies": anomalies}, indent=2)
