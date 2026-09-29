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
- Deterministic AI Growth Analyst query engine with filters, calculations, and evidence metadata
- Canonical cross-platform marketing schema
- Campaign investigation and creative diagnostics
- Cohort and retention analytics
- Auditable evidence packets
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
- analyze_growth_query
- get_metric_definition
- normalize_growth_records
- investigate_campaign
- analyze_creatives
- analyze_cohorts
- build_evidence_packet
- duplicate_campaign

Example analyst queries:

- `Show ROAS and CPL for Launch A`
- `Give campaign performance from 2026-09-01 to 2026-09-30`
- `What is our conversion rate and spend?`

The analyst is deterministic: it calculates only from records supplied to the tool, and its response includes the filtered record count, filters, calculation method, and evidence rows. It does not claim live data or call an external LLM.

The workflow layer provides a canonical schema so Meta, Google, TikTok, CRM, and product-event records can be normalized into common fields. Campaign investigations expose platform/ad-set/creative breakdowns, creative analysis exposes delivery metrics, cohort analysis calculates month-level retention, and evidence packets preserve source rows and calculation limitations.

See examples/mcp-client-config.json for a local MCP client configuration example.

## MCP protocol smoke test

The repository includes a credential-free end-to-end smoke test that starts the real stdio server, initializes an MCP client session, and verifies that the expected growth and Meta Ads tools are registered. It does not call Meta APIs.

Run it locally with:

```bash
pytest -m e2e tests/test_mcp_smoke.py
```

CI runs this smoke test separately from the unit-test matrix.

## Docker

The Docker image runs GrowthMCP as a non-root user and exposes Streamable HTTP on port 8080. Credentials are supplied at runtime rather than baked into the image.

```bash
docker build -t growthmcp .
docker run --rm -p 8080:8080 \
  -e META_ACCESS_TOKEN="$META_ACCESS_TOKEN" \
  growthmcp
```

For anything beyond localhost or a trusted private network, put the service behind your own TLS and authentication layer.

## Security notes

- Keep Meta access tokens and app secrets outside source control.
- The local OAuth flow uses a localhost callback and state validation.
- Streamable HTTP can accept an operator-provided Bearer token; deploy it behind your own authentication and TLS when exposed beyond localhost.
- GrowthMCP does not require or call the upstream hosted MCP service.
