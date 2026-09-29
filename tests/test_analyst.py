from growthmcp.core.analyst import _aggregate, _filter_records, _requested_metrics


def test_aggregate_derives_metrics_from_totals():
    rows = [
        {"spend": 100, "revenue": 300, "impressions": 1000, "clicks": 100, "leads": 10, "conversions": 5},
        {"spend": 50, "revenue": 100, "impressions": 500, "clicks": 50, "leads": 5, "conversions": 5},
    ]
    metrics = _aggregate(rows)
    assert metrics["roas"] == 400 / 150
    assert metrics["ctr"] == 150 / 1500 * 100
    assert metrics["cpl"] == 150 / 15


def test_query_metric_detection():
    metrics = _requested_metrics("show ROAS and cost per lead")
    assert metrics == ["roas", "cpl"]


def test_campaign_and_date_filters():
    rows = [
        {"campaign_name": "Launch A", "date": "2026-09-01", "platform": "Meta", "spend": 10},
        {"campaign_name": "Launch A", "date": "2026-09-20", "platform": "Meta", "spend": 20},
        {"campaign_name": "Launch B", "date": "2026-09-10", "platform": "Google", "spend": 30},
    ]
    filtered, filters = _filter_records(rows, "Launch A 2026-09-01 2026-09-15")
    assert len(filtered) == 1
    assert filters["campaign"] == "launch a"
