"""Deterministic growth issue investigation engine."""

from typing import Any, Dict, List, Optional
import json

from .server import mcp_server
from .workflows import canonicalize_record, _aggregate, _group


def _pct(current: float, previous: float) -> Optional[float]:
    return (current - previous) / previous * 100 if previous else None


def _metric(question: str) -> str:
    q = (question or "").lower()
    for key, phrases in {
        "roas": ("roas", "return on ad spend"),
        "cpl": ("cpl", "cost per lead"),
        "cpa": ("cpa", "cost per acquisition", "cost per conversion"),
        "ctr": ("ctr", "click through rate", "click-through rate"),
        "cpc": ("cpc", "cost per click"),
        "conversion_rate": ("conversion rate", "cvr"),
        "revenue": ("revenue", "sales"),
        "spend": ("spend", "ad spend"),
    }.items():
        if any(p in q for p in phrases):
            return key
    return "roas"


def _delta(cur: Dict[str, float], prev: Dict[str, float], key: str) -> Dict[str, Any]:
    c, p = cur.get(key, 0.0), prev.get(key, 0.0)
    return {"current": c, "previous": p, "change_pct": _pct(c, p)}


def _drivers(cur: Dict[str, float], prev: Dict[str, float], metric: str) -> List[Dict[str, Any]]:
    formulas = {
        "roas": ["revenue", "spend"], "cpl": ["spend", "leads"],
        "cpa": ["spend", "conversions"], "ctr": ["clicks", "impressions"],
        "cpc": ["spend", "clicks"], "conversion_rate": ["conversions", "clicks"],
    }
    keys = formulas.get(metric, [metric])
    return [{"component": k, "delta": _delta(cur, prev, k)} for k in keys]


def _investigation_summary(metric: str, cur: Dict[str, float], prev: Dict[str, float]) -> str:
    if not prev:
        return f"Current-period {metric} is {cur.get(metric, 0.0):.2f}; no previous period was supplied."
    target = _delta(cur, prev, metric)
    change = target["change_pct"]
    if change is None:
        return f"Current-period {metric} is {cur.get(metric, 0.0):.2f}; the previous period has no usable baseline."
    direction = "increased" if change > 0 else "decreased" if change < 0 else "was unchanged"
    components = {
        "roas": ("revenue", "spend"),
        "cpl": ("spend", "leads"),
        "cpa": ("spend", "conversions"),
        "ctr": ("clicks", "impressions"),
        "cpc": ("spend", "clicks"),
        "conversion_rate": ("conversions", "clicks"),
    }.get(metric, ())
    component_text = []
    for key in components:
        delta = _delta(cur, prev, key)["change_pct"]
        if delta is not None:
            component_text.append(f"{key} {delta:+.1f}%")
    suffix = f"; component movements: {', '.join(component_text)}." if component_text else "."
    return f"{metric} {direction} by {abs(change):.1f}%{suffix}"


def _breakdowns(rows: List[Dict[str, Any]], prev: List[Dict[str, Any]], metric: str) -> Dict[str, Any]:
    result = {}
    for dimension in ("platform", "campaign_name", "adset_name", "creative_name"):
        current_groups = _group(rows, dimension)
        previous_groups = _group(prev, dimension)
        result[dimension] = []
        for name, items in current_groups.items():
            cur = _aggregate(items)
            old = _aggregate(previous_groups.get(name, []))
            result[dimension].append({"value": name, "metrics": cur, "comparison": _delta(cur, old, metric)})
    return result


@mcp_server.tool()
async def investigate_growth_issue(question: str, current_records: List[Dict[str, Any]], previous_records: Optional[List[Dict[str, Any]]] = None, user_events: Optional[List[Dict[str, Any]]] = None) -> str:
    """Investigate a growth-metric change with formula drivers and auditable dimensional evidence."""
    if not isinstance(current_records, list) or not current_records:
        return json.dumps({"error": "current_records must be a non-empty list"}, indent=2)
    current = [canonicalize_record(r) for r in current_records if isinstance(r, dict)]
    previous = [canonicalize_record(r) for r in (previous_records or []) if isinstance(r, dict)]
    metric = _metric(question)
    cur = _aggregate(current)
    old = _aggregate(previous) if previous else {}
    result = {
        "question": question, "issue_metric": metric,
        "status": "comparison_available" if previous else "current_period_only",
        "current_metrics": cur, "previous_metrics": old,
        "target_change": _delta(cur, old, metric) if previous else None,
        "summary": _investigation_summary(metric, cur, old),
        "driver_decomposition": _drivers(cur, old, metric) if previous else [],
        "breakdowns": _breakdowns(current, previous, metric) if previous else {},
        "evidence": {"current_record_count": len(current), "previous_record_count": len(previous), "current_rows": current[:50], "previous_rows": previous[:50]},
        "limitations": ["Only supplied records are analyzed.", "Driver consistency does not establish causality.", "Attribution semantics depend on source data."]
    }
    if user_events:
        result["cohort_context"] = {"user_event_count": len([r for r in user_events if isinstance(r, dict)]), "note": "Use analyze_cohorts for detailed retention output."}
    return json.dumps(result, indent=2)
