# GrowthMCP

AI-powered marketing intelligence and Meta Ads MCP.

GrowthMCP is a derivative work built from the Meta Ads MCP server by ARTELL SOLUÇÕES TECNOLÓGICAS LTDA. The upstream work is licensed under Business Source License 1.1; see [LICENSE](LICENSE) for the complete license and current usage terms.

GrowthMCP focuses on a clean, independent product identity while retaining the underlying Meta Ads MCP capabilities that are permitted by the upstream license.

## Core capabilities

- Meta Ads account discovery and account information
- Campaign, ad set, ad, and creative management
- Performance insights and reporting
- Audience and targeting research
- Budget schedules and optimization workflows
- Streamable HTTP and stdio MCP transports
- Configurable Bearer-token authentication and custom Meta app OAuth
- Automated test coverage for core Meta Ads workflows

## Usage

This repository is designed for local/self-hosted development and MCP client integration using your own Meta developer application and credentials.

### Environment

Set the credentials required by your Meta app, for example:

```bash
export META_APP_ID="your-app-id"
export META_APP_SECRET="your-app-secret"
export META_ACCESS_TOKEN="your-access-token"
```

Run the MCP server over stdio:

```bash
python -m growthmcp
```

Run Streamable HTTP:

```bash
python -m growthmcp --transport streamable-http --host 127.0.0.1 --port 8080
```

## License

This repository contains derivative code from the upstream Meta Ads MCP server and therefore retains the upstream Business Source License 1.1. See [LICENSE](LICENSE).

Upstream repository:
https://github.com/pipeboard-co/meta-ads-mcp

Upstream license:
Business Source License 1.1, licensed to ARTELL SOLUÇÕES TECNOLÓGICAS LTDA.
