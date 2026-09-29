"""Deterministic AI Growth Analyst query engine.

This layer turns natural-language growth questions into transparent,
reproducible calculations over records supplied by an MCP client or another
GrowthMCP tool. It does not call an external LLM and never pretends that the
provided records are live data.
"""

import json
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .analytics import _metrics
from .server import mcp_server


METRIC_ALIASES = {
    "roas": "roas",
    "return on ad spend": "roas",
    "revenue": "revenue",
    "spend": "spend",
    "cost": "spend",
    "impressions": "impressions",
    "impression": "impressions",
    "clicks": "clicks",
    "click": "clicks",
    "ctr": "ctr",
    "click through rate": "ctr",
    "cpc": "cpc",
    "cost per click": "cpc",
    "cpa": "cpa",
    "cost per acquisition": "cpa",
    "cpl": "cpl",
    "cost per lead": "cpl",
    "leads": "leads",
    "lead": "leads",
    "conversions": "conversions",
    "conversion": "conversions",
    "conversion rate": "conversion_rate",
    "cvr": "conversion_rate",
}

METRIC_LABELS = {
    "roas": "ROAS",
    "revenue": "revenue",
    "spend": "spend",
    "impressions": "impressions",
    "clicks": "clicks",
    "ctr": "CTR",
    "cpc": "CPC",
    "cpa": "CPA",
    "cpl": "CPL",
    "leads": "leads",
    "conversions": "conversions",
    "conversion_rate": "conversion rate",
}


def _parse_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _metric_from_query(query: str) -> str:
    lowered = query.lower()
    # Prefer longer aliases so "cost per lead" is matched before "lead".
    for alias in sorted(METRIC_ALIASES, key=len, reverse=True):
        if alias in lowered:
            return METRIC_ALIASES[alias]
    return "roas"


def _requested_metrics(query: str) -> List[str]:
    lowered = query.lower()
    found = []
    for alias in sorted(METRIC_ALIASES, key=len, reverse=True):
        if alias in lowered:
            metric = METRIC_ALIASES[alias]
            if metric not in found:
                found.append(metric)
    return found or ["roas"]


def _extract_date_range(query: str) -> Tuple[Optional[str], Optional[str]]:
    matches = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", query)
    if len(matches) >= 2:
        return matches[0], matches[1]
    return None, None


def _filter_records(records: List[Dict[str, Any]], query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    start, end = _extract_date_range(query)
    start_d, end_d = _parse_date(start), _parse_date(end)
    filtered = list(records)

    if start_d and end_d:
        filtered = [
            r for r in filtered
            if (d := _parse_date(r.get("date") or r.get("day") or r.get("event_date"))) is not None
            and start_d <= d <= end_d
        ]

    lowered = query.lower()
    campaign_names = {str(r.get("campaign_name", "")).strip().lower() for r in filtered if r.get("campaign_name")}
    mentioned_campaign = None
    for name in sorted((n for n in campaign_names if n), key=len, reverse=True):
        if name in lowered:
            mentioned_campaign = name
            filtered = [r for r in filtered if str(r.get("campaign_name", "")).strip().lower() == name]
            break

    platform = None
    for candidate in ("meta", "facebook", "instagram", "google", "tiktok", "linkedin", "snapchat", "reddit"):
        if re.search(rf"\b{re.escape(candidate)}\b", lowered):
            platform = candidate
            filtered = [
                r for r in filtered
                if candidate in str(r.get("platform", r.get("source", ""))).lower()
            ]

    return filtered, {
        "date_range": {"since": start, "until": end} if start and end else None,
        "campaign": mentioned_campaign,
        "platform": platform,
    }


def _aggregate(records: List[Dict[str, Any]]) -> Dict[str, float]:
    base = {
        key: sum(float(r.get(key, 0) or 0) for r in records)
        for key in ("spend", "revenue", "impressions", "clicks", "conversions", "leads")
    }
    return _metrics(base)


def _group_by_campaign(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in records:
        key = str(row.get("campaign_name") or row.get("campaign_id") or "Unknown")
        groups.setdefault(key, []).append(row)
    output = []
    for name, rows in groups.items():
        metrics = _aggregate(rows)
        output.append({
            "campaign": name,
            "record_count": len(rows),
            "metrics": metrics,
        })
    return output


def _format_value(metric: str, value: float) -> str:
    if metric in {"ctr", "conversion_rate"}:
        return f"{value:.2f}%"
    if metric == "roas":
        return f"{value:.2f}x"
    if metric in {"cpc", "cpa", "cpl", "spend", "revenue"}:
        return f"{value:.2f}"
    if metric in {"impressions", "clicks", "leads", "conversions"}:
        return f"{value:.0f}"
    return f"{value:.2f}"


def _answer(query: str, records: List[Dict[str, Any]], metrics: List[str]) -> Dict[str, Any]:
    lowered = query.lower()
    grouped = any(token in lowered for token in ("campaigns", "campaign performance", "by campaign", "each campaign"))
    if grouped:
        groups = _group_by_campaign(records)
        return {
            "answer_type": "campaign_breakdown",
            "results": [
                {
                    "campaign": row["campaign"],
                    "record_count": row["record_count"],
                    "metrics": {m: row["metrics"][m] for m in metrics},
                }
                for row in groups
            ],
        }

    totals = _aggregate(records)
    values = {m: totals[m] for m in metrics}
    text = ", ".join(f"{METRIC_LABELS[m]} {_format_value(m, values[m])}" for m in metrics)
    return {
        "answer_type": "summary",
        "summary": text,
        "metrics": values,
    }


@mcp_server.tool()
async def analyze_growth_query(
    query: str,
    records: List[Dict[str, Any]],
    source: str = "client-supplied",
) -> str:
    """Answer a natural-language growth analytics question over supplied records.

    Supported filters include campaign names, common platforms, and explicit
    ISO date ranges such as 2026-09-01 to 2026-09-30. Supported metrics include
    ROAS, revenue, spend, CTR, CPC, CPA, CPL, leads, conversions and conversion
    rate. Queries mentioning campaigns can return a campaign-level breakdown.

    The response includes the exact filtered record count and calculation
    metadata so an analyst can audit the answer.
    """
    if not isinstance(query, str) or not query.strip():
        return json.dumps({"error": "query must be a non-empty string"}, indent=2)
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        return json.dumps({"error": "records must be a list of objects"}, indent=2)

    filtered, filters = _filter_records(records, query)
    metrics = _requested_metrics(query)

    if not filtered:
        return json.dumps({
            "query": query,
            "source": source,
            "filters": filters,
            "record_count": 0,
            "answer": "No matching records were found.",
            "evidence": [],
        }, indent=2)

    result = _answer(query, filtered, metrics)
    return json.dumps({
        "query": query,
        "source": source,
        "record_count": len(filtered),
        "filters": filters,
        "metrics_requested": metrics,
        "calculation": "Aggregated additive fields first, then derived CTR/CPC/CPA/CPL/conversion rate/ROAS from the aggregate totals.",
        "answer": result,
        "evidence": [
            {
                "campaign_name": r.get("campaign_name"),
                "date": r.get("date") or r.get("day") or r.get("event_date"),
                "source": r.get("source") or r.get("platform") or source,
            }
            for r in filtered[:25]
        ],
    }, indent=2)


@mcp_server.tool()
async def get_metric_definition(metric: str) -> str:
    """Return a concise definition and calculation formula for a growth metric."""
    normalized = METRIC_ALIASES.get(metric.lower().strip(), metric.lower().strip())
    definitions = {
        "roas": ("Return on ad spend", "revenue / spend"),
        "ctr": ("Click-through rate", "clicks / impressions × 100"),
        "cpc": ("Cost per click", "spend / clicks"),
        "cpa": ("Cost per acquisition", "spend / conversions"),
        "cpl": ("Cost per lead", "spend / leads"),
        "conversion_rate": ("Conversion rate", "conversions / clicks × 100"),
        "spend": ("Advertising spend", "sum of spend"),
        "revenue": ("Attributed revenue", "sum of revenue"),
        "impressions": ("Ad impressions", "sum of impressions"),
        "clicks": ("Ad clicks", "sum of clicks"),
        "leads": ("Leads", "sum of leads"),
        "conversions": ("Conversions", "sum of conversions"),
    }
    if normalized not in definitions:
        return json.dumps({"error": f"Unknown metric: {metric}", "available_metrics": sorted(definitions)}, indent=2)
    label, formula = definitions[normalized]
    return json.dumps({"metric": normalized, "label": label, "formula": formula}, indent=2)
