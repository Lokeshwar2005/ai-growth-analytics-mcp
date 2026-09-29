# Security

GrowthMCP is intended to run with credentials owned and controlled by the operator.

## Principles

- Prefer short-lived or least-privilege Meta credentials where supported.
- Never commit access tokens or app secrets.
- Keep `.env` files out of source control.
- Review write operations before enabling them in production.
- Use HTTPS when exposing Streamable HTTP outside localhost.
- Rotate credentials if they are accidentally exposed.

This project does not include a hosted GrowthMCP service. Any deployment infrastructure should be configured and secured by the operator.
