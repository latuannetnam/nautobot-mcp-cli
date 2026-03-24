# Requirements: nautobot-mcp-cli v1.3

**Defined:** 2026-03-24
**Core Value:** AI agents can read and write Nautobot data through standardized MCP tools — with minimal context window overhead and maximum tool selection accuracy.

## v1.3 Requirements

_Pending — to be defined by gsd-new-milestone workflow for API Bridge MCP Server._

Previous v1.3 "Generic Resource Engine" requirements (30 total) were rejected on 2026-03-24 before implementation. Superseded by API Bridge architecture.

See: [API Bridge Design](../docs/plans/2026-03-24-api-bridge-mcp-design.md)

## Future Requirements

### Multi-Domain Scaling

- **SCALE-01**: When adding a new domain, only catalog entries needed (zero new `@mcp.tool` definitions)
- **SCALE-02**: Split into multiple MCP sub-servers when tool count exceeds 40

### Extended Tooling

- **EXT-01**: Multi-vendor config parsers (Cisco IOS/IOS-XE, Arista EOS)
- **EXT-02**: Bulk device onboarding (batch config files)
- **EXT-03**: Config remediation suggestions based on drift reports

## Out of Scope

| Feature | Reason |
|---------|--------|
| CLI refactoring | CLI calls domain modules directly — unaffected by MCP layer changes |
| Backwards-compatible tool aliases | Defeats purpose; would double tool count |
| Dynamic tool generation from registry | Harder to debug, IDE unfriendly |
| GraphQL integration | Different query paradigm, not needed |
| Real-time LLM caching | Stale data risk, context bloat |

---
*Requirements reset: 2026-03-24 — Generic Resource Engine rejected, API Bridge pending*
