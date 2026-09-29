# GrowthMCP

**AI-powered marketing intelligence and Meta Ads MCP.**

GrowthMCP is a derivative project built from the Meta Ads MCP server by **ARTELL SOLUÇÕES TECNOLÓGICAS LTDA**. The upstream work is licensed under **Business Source License 1.1**; the required license text is retained in [LICENSE](LICENSE).

## 🚀 Live Demo & Deployment Status

> **Frontend Dashboard Status**: Not currently publicly deployed.
>
> GrowthMCP is an independent, self-hosted Model Context Protocol (MCP) server rather than a static website. It serves marketing intelligence and Meta Ads tools via `stdio` and Streamable HTTP transports.
>
> - **Interactive Inspection**: Full interactive UI testing is available locally via the official [MCP Inspector](docs/MCP_INSPECTOR.md).
> - **Prerequisite for Public Demo**: A deployed web frontend client application configured to connect to GrowthMCP's Streamable HTTP transport endpoint.

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

## Inspecting with MCP Inspector

GrowthMCP is fully compatible with `@modelcontextprotocol/inspector@2.8.0`.

### Web Inspector
Launch the interactive browser UI to test tools and inspect schemas:

```bash
cd ~/ai-growth-analytics-mcp

npx -y @modelcontextprotocol/inspector@2.8.0 \
  -e META_ACCESS_TOKEN="$META_ACCESS_TOKEN" \
  -- python3 -m growthmcp
```

### CLI Inspector
Run headless inspections and tool invocations:

```bash
# Handshake initialization
npx -y @modelcontextprotocol/inspector@2.8.0 --cli \
  python3 -m growthmcp \
  -- \
  --method initialize

# List tools
npx -y @modelcontextprotocol/inspector@2.8.0 --cli \
  python3 -m growthmcp \
  -- \
  --method tools/list

# Call analyze_growth_query
npx -y @modelcontextprotocol/inspector@2.8.0 --cli \
  python3 -m growthmcp \
  -- \
  --method tools/call \
  --tool-name analyze_growth_query \
  --tool-args-json '{"query":"What is the ROAS?","records":[{"date":"2026-09-21","platform":"Meta","campaign_name":"Brand Search","spend":120,"revenue":300,"impressions":12000,"clicks":240},{"date":"2026-09-21","platform":"Meta","campaign_name":"Prospecting","spend":300,"revenue":200,"impressions":40000,"clicks":600}]}'
```

> **Note on Inspector 2.8.0 Syntax**: The important point is that Python's `-m growthmcp` must remain part of the target command. The Inspector separator `--` separates the target command from Inspector options.
> If GrowthMCP is installed in the active environment, the package binary can also be called directly:
> ```bash
> npx -y @modelcontextprotocol/inspector@2.8.0 --cli growthmcp --method initialize
> ```
> See [docs/MCP_INSPECTOR.md](docs/MCP_INSPECTOR.md) for full details and troubleshooting.



## MCP protocol smoke test

The repository includes a credential-free end-to-end smoke test that starts the real stdio server, initializes an MCP client session, and verifies that the expected growth and Meta Ads tools are registered. It does not call Meta APIs.

Run it locally with:

```bash
pytest -m e2e tests/test_mcp_smoke.py
```

CI runs this smoke test separately from the unit-test matrix.

### Optional live Meta API validation

A separate opt-in test can validate the full path against a real Meta Ads account without storing credentials in the repository or CI. It requests the last 7 days of campaign insights, normalizes the returned rows, and runs the GrowthMCP analyst on the live data.

Set these only in your local shell:

```bash
export GROWTHMCP_LIVE_META_TEST=1
export META_ACCESS_TOKEN="your-access-token"
export GROWTHMCP_META_ACCOUNT_ID="act_123456789"
pytest -m live tests/test_meta_live.py
```

The live test is excluded from the default test suite and GitHub Actions. Never commit the access token or app secret.

The `investigate_live_meta_growth_issue` tool fetches two bounded Meta Insights periods, follows pagination up to a configurable page limit, normalizes Meta action arrays, and passes the records into the deterministic investigation engine. It is read-only.

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
