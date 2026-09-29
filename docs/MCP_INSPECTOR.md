# Using MCP Inspector with GrowthMCP

This guide provides instructions and troubleshooting for connecting **GrowthMCP** to the official **MCP Inspector** (`@modelcontextprotocol/inspector@2.8.0`).

---

## Environment & Compatibility Matrix

| Component | Tested Version | Notes |
| :--- | :--- | :--- |
| **Python** | 3.11+ | Runtime environment |
| **MCP SDK** | `mcp[cli]==1.28.1` | FastMCP server library |
| **MCP Inspector** | `@modelcontextprotocol/inspector@2.8.0` | Official MCP debugging tool |
| **Protocol Negotiation** | `2024-11-05` / `2025-11-25` | Handshake negotiated dynamically by the MCP client during initialize (direct stdio client negotiates `2024-11-05`; Inspector negotiates `2025-11-25`). GrowthMCP code is not pinned or altered. |

---

## 1. Quick Start: Web Inspector

The MCP Inspector Web UI provides an interactive browser-based interface to inspect tools, prompts, and resources.

### Option A: Ad-Hoc Command (Recommended)

To launch the Web Inspector and connect to GrowthMCP over stdio:

```bash
cd ~/ai-growth-analytics-mcp

npx -y @modelcontextprotocol/inspector@2.8.0 \
  -e META_ACCESS_TOKEN="$META_ACCESS_TOKEN" \
  -- python3 -m growthmcp
```

> **Note on Web Syntax**: In Inspector Web UI mode, any Inspector flags (such as `-e`) come **before** `--`, and the target server command comes **after** `--`.

### Option B: Using a Configuration File

You can also point Inspector to an MCP client configuration file:

```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --config examples/mcp-client-config.json
```

---

## 2. CLI Inspector (Headless / Automated Verification)

The CLI mode (`--cli`) runs one-shot operations against GrowthMCP.

### Important: Argument Ordering in Inspector 2.8.0 CLI

Inspector 2.8.0 CLI uses an argument parser that interprets tokens starting with `-` as Inspector options unless shielded. When running `python3 -m growthmcp`, Python's `-m growthmcp` must remain part of the target command.

The Inspector separator `--` separates the target command from Inspector options:

```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --cli <target-command> -- <inspector-options>
```

### A. Initialize Handshake

```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --cli \
  python3 -m growthmcp \
  -- \
  --method initialize
```

Expected result: returns JSON with `serverInfo.name = "growthmcp"`, `protocolVersion = "2025-11-25"`, and exit code `0`.

### B. List Available Tools

```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --cli \
  python3 -m growthmcp \
  -- \
  --method tools/list
```

Expected result: returns the registered GrowthMCP growth and Meta tools.

### C. Call a Tool (`analyze_growth_query`)

```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --cli \
  python3 -m growthmcp \
  -- \
  --method tools/call \
  --tool-name analyze_growth_query \
  --tool-args-json '{"query":"What is the ROAS?","records":[{"date":"2026-09-21","platform":"Meta","campaign_name":"Brand Search","spend":120,"revenue":300,"impressions":12000,"clicks":240},{"date":"2026-09-21","platform":"Meta","campaign_name":"Prospecting","spend":300,"revenue":200,"impressions":40000,"clicks":600}]}'
```

Expected result: returns calculated metrics including `"summary": "ROAS 1.19x"`, `isError: false`.

### D. Passing Environment Variables

Pass environment variables using `-e KEY=VALUE` after the `--` separator:

```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --cli \
  python3 -m growthmcp \
  -- \
  -e "META_ACCESS_TOKEN=$META_ACCESS_TOKEN" \
  --method tools/call \
  --tool-name get_ad_accounts
```

### E. Verified Package-Binary Alternative

When GrowthMCP is installed in the active Python environment (`pip install -e .`), the entrypoint binary `growthmcp` can also be invoked directly:

```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --cli growthmcp --method initialize
npx -y @modelcontextprotocol/inspector@2.8.0 --cli growthmcp --method tools/list
```

Because `growthmcp` contains no leading hyphen, Inspector's parser treats it as the complete target command even without an explicit `--`.

---

## 3. Troubleshooting & Root Cause Analysis

### Issue: `NameError: name 'true' is not defined` & Timeout after 15000 ms

#### Cause:
In Inspector 2.8.0 CLI (`clients/cli/build/index.js`), the ad-hoc target parser stops collecting target arguments as soon as it encounters any token beginning with `-`:
```javascript
let i = 0;
while (i < scriptArgs.length && !scriptArgs[i].startsWith("-")) {
  targetArgs.push(scriptArgs[i]);
  i++;
}
optionArgs = scriptArgs.slice(i);
```
When invoked without `--`:
```bash
# FAILS:
npx -y @modelcontextprotocol/inspector@2.8.0 --cli python3 -m growthmcp --method initialize
```
1. `python3` does not start with `-`, so it is added to `targetArgs`.
2. `-m` starts with `-`, terminating the loop immediately.
3. As a result, `targetArgs` is truncated to `["python3"]` with **no arguments**, while `["-m", "growthmcp", "--method", "initialize"]` is treated as Inspector options.
4. Inspector effectively launched `python3` instead of `python3 -m growthmcp`.
5. Python entered interactive mode and received MCP JSON containing lowercase JSON booleans such as `true`.
6. Python interpreted that as Python source and raised:
   ```
   Traceback (most recent call last):
     File "<stdin>", line 1, in <module>
   NameError: name 'true' is not defined. Did you mean: 'True'?
   ```
7. Inspector subsequently timed out waiting for an MCP response:
   ```
   Connection timed out after 15000 ms
   ```

#### Solution:
Provide the explicit `--` separator so `-m growthmcp` remains part of the target command:
```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --cli \
  python3 -m growthmcp \
  -- \
  --method initialize
```
Or use the installed `growthmcp` package binary directly:
```bash
npx -y @modelcontextprotocol/inspector@2.8.0 --cli growthmcp --method initialize
```

---

### Issue: `spawn --version ENOENT` / Failed to connect to `--version`

#### Cause:
Running:
```bash
npx -y @modelcontextprotocol/inspector --version
```
caused `spawn --version ENOENT` because the command launched Web Inspector mode rather than functioning as a normal version-print command. The launcher treats `--version` as the server executable to spawn.

#### Solution:
Check Inspector version via `npm`:
```bash
npm info @modelcontextprotocol/inspector version
# or
npx -y @modelcontextprotocol/inspector@2.8.0 --help
```

---

### Issue: `{"error":{"code":"error","message":"No servers found in config file"}}`

#### Cause:
When Inspector CLI cannot extract an ad-hoc target (e.g. when flags are placed before the command without a recognized target), it falls back to reading the default catalog (`~/.mcp-inspector/mcp.json`). If that file contains an empty `mcpServers: {}` object, Inspector reports `No servers found in config file`.

#### Solution:
Ensure the target command is supplied before `--` or pass `--config path/to/config.json`.
