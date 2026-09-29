"""GrowthMCP core tool registry."""
from .server import mcp_server
from .accounts import get_ad_accounts, get_account_info
from .campaigns import get_campaigns, get_campaign_details, create_campaign, update_campaign
from .adsets import get_adsets, get_adset_details, create_adset, update_adset
from .ads import (
    get_ads, get_ad_details, get_creative_details, create_ad,
    get_ad_creatives, get_ad_image, get_image_by_hash, get_ad_video,
    update_ad, upload_ad_image, compute_image_crops, create_ad_creative,
    update_ad_creative, search_pages_by_name, get_account_pages,
)
from .insights import get_insights
from .auth import login
from .server import login_cli, main
from .budget_schedules import create_budget_schedule
from .targeting import (
    search_interests, get_interest_suggestions, estimate_audience_size,
    search_behaviors, search_demographics, search_geo_locations,
)
from .duplication import duplicate_campaign
from .analytics import calculate_growth_metrics, compare_campaign_metrics, detect_metric_anomalies
from .analyst import analyze_growth_query, get_metric_definition
from .workflows import normalize_growth_records, investigate_campaign, analyze_creatives, analyze_cohorts, build_evidence_packet
from .investigation import investigate_growth_issue
from . import authentication, ads_library, reports

__all__ = [
    "mcp_server", "get_ad_accounts", "get_account_info",
    "get_campaigns", "get_campaign_details", "create_campaign", "update_campaign",
    "get_adsets", "get_adset_details", "create_adset", "update_adset",
    "get_ads", "get_ad_details", "get_creative_details", "create_ad",
    "get_ad_creatives", "get_ad_image", "get_image_by_hash", "get_ad_video",
    "update_ad", "upload_ad_image", "compute_image_crops", "create_ad_creative",
    "update_ad_creative", "search_pages_by_name", "get_account_pages",
    "get_insights", "login", "login_cli", "main", "create_budget_schedule",
    "search_interests", "get_interest_suggestions", "estimate_audience_size",
    "search_behaviors", "search_demographics", "search_geo_locations",
    "duplicate_campaign", "calculate_growth_metrics", "compare_campaign_metrics",
    "detect_metric_anomalies", "analyze_growth_query", "get_metric_definition",
    "normalize_growth_records", "investigate_campaign", "analyze_creatives",
    "analyze_cohorts", "build_evidence_packet", "investigate_growth_issue",
]
