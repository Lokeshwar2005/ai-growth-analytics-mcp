from growthmcp.core.workflows import canonicalize_record, _aggregate


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
