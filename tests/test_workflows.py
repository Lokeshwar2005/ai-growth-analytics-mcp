import json

import pytest

from growthmcp.core.workflows import canonicalize_record, _aggregate, analyze_cohorts
from growthmcp.core.investigation import _drivers, _metric, investigate_growth_issue


def test_canonicalize_common_platform_fields():
    row = {"day": "2026-09-01", "cost": "100", "link_clicks": 20, "purchase_value": 250}
    result = canonicalize_record(row, "google")
    assert result["date"] == "2026-09-01"
    assert result["spend"] == 100.0
    assert result["clicks"] == 20.0
    assert result["revenue"] == 250.0
    assert result["source"] == "google"


def test_workflow_aggregate_uses_aggregate_rates():
    result = _aggregate([
        {"spend": 100, "revenue": 200, "impressions": 1000, "clicks": 100, "leads": 10, "conversions": 5},
        {"spend": 100, "revenue": 300, "impressions": 1000, "clicks": 50, "leads": 10, "conversions": 5},
    ])
    assert result["roas"] == 2.5
    assert result["ctr"] == 7.5


@pytest.mark.asyncio
async def test_cohort_uses_earliest_event_month():
    events = [
        {"user_id": "u1", "event_date": "2026-02-10", "event_name": "purchase"},
        {"user_id": "u1", "event_date": "2026-01-05", "event_name": "signup"},
        {"user_id": "u1", "event_date": "2026-03-01", "event_name": "session"},
        {"user_id": "u2", "event_date": "2026-01-20", "event_name": "signup"},
    ]
    result = json.loads(await analyze_cohorts(events))
    cohort = next(item for item in result["cohorts"] if item["cohort"] == "2026-01")
    assert cohort["cohort_users"] == 2
    assert cohort["retention"]["month_0"]["active_users"] == 2
    assert cohort["retention"]["month_1"]["active_users"] == 1
    assert cohort["retention"]["month_2"]["active_users"] == 1


def test_investigation_detects_roas_and_drivers():
    assert _metric("Why did ROAS drop?") == "roas"
    drivers = _drivers({"revenue": 80, "spend": 120}, {"revenue": 100, "spend": 100}, "roas")
    assert {d["component"] for d in drivers} == {"revenue", "spend"}
    assert drivers[0]["delta"]["change_pct"] == -20.0
    assert drivers[1]["delta"]["change_pct"] == 20.0


@pytest.mark.asyncio
async def test_investigation_tool_returns_driver_evidence():
    current = [
        {"date": "2026-09-10", "campaign_name": "Search", "spend": 120, "revenue": 80},
    ]
    previous = [
        {"date": "2026-09-03", "campaign_name": "Search", "spend": 100, "revenue": 100},
    ]
    result = json.loads(await investigate_growth_issue(
        "Why did ROAS drop?",
        current_records=current,
        previous_records=previous,
    ))
    assert result["issue_metric"] == "roas"
    assert result["target_change"]["change_pct"] == -33.333333333333336
    assert {item["component"] for item in result["driver_decomposition"]} == {"revenue", "spend"}
    assert result["evidence"]["current_record_count"] == 1


def test_canonicalize_meta_action_arrays():
    row = {
        "campaign_name": "Meta Search",
        "spend": "120",
        "impressions": "1000",
        "clicks": "50",
        "actions": [
            {"action_type": "lead", "value": "8"},
            {"action_type": "purchase", "value": "3"},
        ],
        "action_values": [{"action_type": "purchase", "value": "360"}],
    }
    result = canonicalize_record(row, "meta-live")
    assert result["leads"] == 8.0
    assert result["conversions"] == 3.0
    assert result["revenue"] == 360.0
