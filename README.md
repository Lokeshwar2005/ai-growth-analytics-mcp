# GrowthMCP

**AI-powered marketing intelligence and Meta Ads MCP.**

GrowthMCP is a derivative project built from the Meta Ads MCP server by **ARTELL SOLUÇÕES TECNOLÓGICAS LTDA**. The upstream work is licensed under **Business Source License 1.1**; the required license text is retained in [LICENSE](LICENSE).

## What is included

- Meta Ads account discovery and account information
- Campaign, ad set, and ad operations
- Creative operations and performance insights
- Audience and targeting research
- Budget scheduling
- Native campaign duplication through Meta Graph API
- Growth analytics: ROAS, CPA, CPL, CTR, CPC, conversion rate, and anomaly detection
- Local OAuth authentication with your own Meta developer application
- Bearer-token authentication for Streamable HTTP
- stdio and Streamable HTTP MCP transports
- Docker support

## Quick start

Create a Meta developer application and use your own credentials.

```bash
export META_APP_ID="your-app-id"
export META_APP_SECRET="your-app-secret"
export META_ACCESS_TOKEN="your-access-token"
```

Install:

```bash
pip install -e .
```

Run with stdio:

```bash
python -m growthmcp
```

Run Streamable HTTP:

```bash
python -m growthmcp --transport streamable-http --host 127.0.0.1 --port 8080
```

Authenticate through the local OAuth flow:

```bash
python -m growthmcp --login
```

## Branding

GrowthMCP uses its own product name and original visual identity. It does not use Pipeboard-hosted authentication or service infrastructure.

## License and attribution

This repository contains derivative code from the upstream Meta Ads MCP server and therefore retains the upstream **Business Source License 1.1**.

Upstream project:
https://github.com/pipeboard-co/meta-ads-mcp

The upstream license text and attribution are intentionally retained. GrowthMCP branding does not transfer or imply ownership of the upstream work.

## Growth analytics layer

The analytics tools are intentionally platform-neutral. They accept metric records from Meta insights or other systems and calculate common acquisition metrics without requiring a hosted analytics service.

Available tools include:

- calculate_growth_metrics
- compare_campaign_metrics
- detect_metric_anomalies
- duplicate_campaign

See examples/mcp-client-config.json for a local MCP client configuration example.

## Security notes

- Keep Meta access tokens and app secrets outside source control.
- The local OAuth flow uses a localhost callback and state validation.
- Streamable HTTP can accept an operator-provided Bearer token; deploy it behind your own authentication and TLS when exposed beyond localhost.
- GrowthMCP does not require or call the upstream hosted MCP service.
