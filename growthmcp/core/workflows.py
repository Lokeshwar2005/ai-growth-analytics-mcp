"""Growth investigation workflows for GrowthMCP.

The workflows are deterministic and operate on records supplied by the caller.
They provide canonicalization, campaign investigation, creative diagnostics,
cohort/retention summaries, and auditable evidence packets.
"""

import json
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

from .analytics import _metrics
from .server import mcp_server


CANONICAL_FIELDS = (
    "date", "source", "platform", "account_id", "campaign_id",
    "campaign_name", "adset_id", "adset_name", "ad_id", "ad_name",
    "creative_id", "creative_name", "spend", "revenue", "impressions",
    "clicks", "leads", "conversions",
)


def _num(row: Dict[str, Any], key: str) -> float:
    try:
        return float(row.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def canonicalize_record(row: Dict[str, Any], source: str = "unknown") -> Dict[str, Any]:
    """Map common ad-platform field names into GrowthMCP's canonical schema."""
    aliases = {
        "date": ("date", "day", "event_date", "date_start"),
        "source": ("source",),
        "platform": ("platform", "publisher_platform", "network"),
        "account_id": ("account_id", "ad_account_id", "customer_id"),
        "campaign_id": ("campaign_id",),
        "campaign_name": ("campaign_name",),
        "adset_id": ("adset_id", "ad_set_id"),
        "adset_name": ("adset_name", "ad_set_name"),
        "ad_id": ("ad_id",),
        "ad_name": ("ad_name",),
        "creative_id": ("creative_id",),
        "creative_name": ("creative_name",),
        "spend": ("spend", "cost", "amount_spent"),
        "revenue": ("revenue", "purchase_value", "conversion_value"),
        "impressions": ("impressions",),
        "clicks": ("clicks", "link_clicks"),
        "leads": ("leads",),
        "conversions": ("conversions", "purchases", "results"),
    }
    result = {}
    for field, candidates in aliases.items():
        value = next((row.get(k) for k in candidates if row.get(k) is not None), None)
        if field == "source" and not value:
            value = source
        result[field] = value
    for key in ("spend", "revenue", "impressions", "clicks", "leads", "conversions"):
        result[key] = _num(result, key)
    return result


def _aggregate(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    base = {k: sum(_num(r, k) for r in rows)
            for k in ("spend", "revenue", "impressions", "clicks", "leads", "conversions")}
    return _metrics(base)


def _group(rows: List[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    out = defaultdict(list)
    for row in rows:
        out[str(row.get(key) or "Unknown")].append(row)
    return dict(out)


@mcp_server.tool()
async def normalize_growth_records(
    records: List[Dict[str, Any]],
    source: str = "unknown",
) -> str:
    """Normalize heterogeneous marketing records into the canonical GrowthMCP schema."""
    if not isinstance(records, list):
        return json.dumps({"error": "records must be a list of objects"}, indent=2)
    normalized = [canonicalize_record(r, source) for r in records if isinstance(r, dict)]
    return json.dumps({
        "schema": list(CANONICAL_FIELDS),
        "record_count": len(normalized),
        "records": normalized,
    }, indent=2)


@mcp_server.tool()
async def investigate_campaign(
    campaign_name: str,
    records: List[Dict[str, Any]],
    compare_period_records: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build an auditable campaign investigation packet with metrics, drivers, and evidence."""
    if not campaign_name.strip():
        return json.dumps({"error": "campaign_name is required"}, indent=2)
    rows = [canonicalize_record(r) for r in records if isinstance(r, dict)]
    target = campaign_name.strip().lower()
    matched = [r for r in rows if str(r.get("campaign_name") or "").lower() == target]
    if not matched:
        return json.dumps({"campaign": campaign_name, "record_count": 0, "status": "not_found"}, indent=2)

    metrics = _aggregate(matched)
    breakdowns = {}
    for key in ("platform", "creative_name", "adset_name"):
        groups = _group(matched, key)
        breakdowns[key] = [
            {"dimension": name, "record_count": len(items), "metrics": _aggregate(items)}
            for name, items in groups.items()
        ]

    comparison = None
    if compare_period_records:
        compare = [canonicalize_record(r) for r in compare_period_records if isinstance(r, dict)]
        compare = [r for r in compare if str(r.get("campaign_name") or "").lower() == target]
        if compare:
            previous = _aggregate(compare)
            comparison = {
                metric: {"current": metrics[metric], "previous": previous[metric],
                         "change_pct": ((metrics[metric] - previous[metric]) / previous[metric] * 100)
                         if previous[metric] else None}
                for metric in ("spend", "revenue", "ctr", "cpc", "cpl", "roas", "conversions")
            }

    return json.dumps({
        "campaign": campaign_name,
        "status": "found",
        "record_count": len(matched),
        "metrics": metrics,
        "breakdowns": breakdowns,
        "period_comparison": comparison,
        "evidence": [
            {"date": r.get("date"), "adset_name": r.get("adset_name"),
             "creative_name": r.get("creative_name"), "platform": r.get("platform")}
            for r in matched[:50]
        ],
    }, indent=2)


@mcp_server.tool()
async def analyze_creatives(records: List[Dict[str, Any]]) -> str:
    """Analyze creative-level delivery and acquisition metrics without ranking creatives."""
    rows = [canonicalize_record(r) for r in records if isinstance(r, dict)]
    groups = _group(rows, "creative_name")
    results = []
    for name, items in groups.items():
        results.append({
            "creative": name,
            "record_count": len(items),
            "metrics": _aggregate(items),
            "evidence": [
                {"date": r.get("date"), "campaign": r.get("campaign_name"), "ad": r.get("ad_name")}
                for r in items[:10]
            ],
        })
    return json.dumps({"creative_count": len(results), "creatives": results}, indent=2)


def _cohort_month(value: Any) -> Optional[str]:
    try:
        d = date.fromisoformat(str(value)[:10])
        return d.strftime("%Y-%m")
    except (TypeError, ValueError):
        return None


@mcp_server.tool()
async def analyze_cohorts(
    user_events: List[Dict[str, Any]],
) -> str:
    """Calculate cohort sizes and month-level retention from user event records.

    Expected fields: user_id, event_date/date, and event_name. The earliest valid
    event month for each user is treated as that user's acquisition cohort.
    """
    user_cohorts: Dict[str, str] = {}
    user_activity: Dict[str, set] = defaultdict(set)

    for row in user_events:
        if not isinstance(row, dict):
            continue
        uid = row.get("user_id") or row.get("customer_id")
        month = _cohort_month(row.get("event_date") or row.get("date"))
        if not uid or not month:
            continue

        uid = str(uid)
        user_activity[uid].add(month)
        current_cohort = user_cohorts.get(uid)
        if current_cohort is None or month < current_cohort:
            user_cohorts[uid] = month

    cohorts: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"users": set(), "active": defaultdict(set)}
    )
    for uid, cohort in user_cohorts.items():
        cohorts[cohort]["users"].add(uid)
        for month in user_activity[uid]:
            if month >= cohort:
                cohorts[cohort]["active"][month].add(uid)

    output = []
    for cohort, data in sorted(cohorts.items()):
        size = len(data["users"])
        retention = {}
        for month, active in sorted(data["active"].items()):
            months_since = (
                (int(month[:4]) - int(cohort[:4])) * 12
                + int(month[5:7]) - int(cohort[5:7])
            )
            retention[f"month_{months_since}"] = {
                "active_users": len(active),
                "retention_pct": len(active) / size * 100 if size else 0.0,
            }
        output.append({
            "cohort": cohort,
            "cohort_users": size,
            "retention": retention,
        })

    return json.dumps({"cohort_count": len(output), "cohorts": output}, indent=2)


@mcp_server.tool()
async def build_evidence_packet(
    question: str,
    records: List[Dict[str, Any]],
    source: str = "client-supplied",
) -> str:
    """Create a compact audit packet tying a business question to source rows and calculations."""
    rows = [canonicalize_record(r, source) for r in records if isinstance(r, dict)]
    metrics = _aggregate(rows) if rows else {}
    return json.dumps({
        "question": question,
        "source": source,
        "record_count": len(rows),
        "calculation": "Canonicalized records, summed additive metrics, then derived rate metrics from aggregate totals.",
        "metrics": metrics,
        "evidence_rows": rows[:50],
        "limitations": [
            "Only supplied records are analyzed.",
            "No claim is made that the records are live or complete.",
            "Attribution semantics depend on the source platform and supplied fields.",
        ],
    }, indent=2)
