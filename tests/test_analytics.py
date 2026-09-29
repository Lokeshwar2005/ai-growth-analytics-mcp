import json
import pytest
from growthmcp.core.analytics import calculate_growth_metrics, detect_metric_anomalies

@pytest.mark.asyncio
async def test_growth_metrics():
    result = json.loads(await calculate_growth_metrics([{
        "campaign_id": "c1", "spend": 100, "revenue": 300,
        "impressions": 10000, "clicks": 200, "conversions": 10, "leads": 20
    }]))
    row = result["records"][0]
    assert row["ctr"] == 2.0
    assert row["cpc"] == 0.5
    assert row["cpa"] == 10.0
    assert row["cpl"] == 5.0
    assert row["roas"] == 3.0

@pytest.mark.asyncio
async def test_anomaly_detection():
    result = json.loads(await detect_metric_anomalies([10, 10, 10, 100], 1.5))
    assert result["anomalies"]
