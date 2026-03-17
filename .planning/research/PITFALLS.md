# Pitfalls Research: Nautobot MCP CLI

## Critical Pitfalls

### 1. Nautobot API Pagination Trap
**Warning signs:** Queries returning only 50 results, missing devices/interfaces
**What goes wrong:** Nautobot REST API paginates by default. Raw requests miss subsequent pages.
**Prevention:** Use pynautobot's `.all()` which handles pagination automatically. Never use raw requests for list operations.
**Phase:** Phase 1 (Core client)

### 2. API Version Mismatch
**Warning signs:** 404 errors, unexpected field names, missing endpoints
**What goes wrong:** Nautobot 2.x changed many API endpoints from NetBox heritage. Golden Config plugin API may also differ between versions.
**Prevention:** Pin pynautobot version compatible with target Nautobot server. Use `api_version` parameter. Test against actual server early.
**Phase:** Phase 1 (Core client)

### 3. MCP Tool Design — Too Granular vs Too Coarse
**Warning signs:** Agent making 50+ calls for one task, or tools returning excessive data
**What goes wrong:** If tools are too fine-grained (e.g., one tool per CRUD op per model), agents waste tokens on orchestration. If too coarse (e.g., "do everything"), agents can't compose workflows.
**Prevention:** Design tools at the "task level" — `get_device_with_interfaces` is better than `get_device` + `list_interfaces` for common use cases. Provide both atomic and composite tools.
**Phase:** Phase 2 (MCP server layer)

### 4. Config Parsing Fragility
**Warning signs:** Parser breaks on config variants, missing sections
**What goes wrong:** JunOS configs vary by platform (MX vs EX vs SRX), software version, and config style (set vs hierarchy). Regex/template parsers break on unexpected formats.
**Prevention:** Start with hierarchical (curly-brace) format parsing. Use JunOS's structured output where possible. Build extensive test fixtures from real configs. Handle missing sections gracefully.
**Phase:** Phase 3 (Config parsers)

### 5. Nautobot Object Reference Resolution
**Warning signs:** "Device type not found", "Location required", foreign key errors
**What goes wrong:** Creating objects in Nautobot requires resolving references (device type, location, manufacturer). These must exist before creating dependent objects.
**Prevention:** Build a resolution layer that looks up or creates prerequisite objects. Use pynautobot's nested object handling. Implement a dry-run mode that validates references before committing.
**Phase:** Phase 1-2 (Core client + onboarding)

### 6. Golden Config Plugin API Assumptions
**Warning signs:** Endpoints not found, unexpected data formats
**What goes wrong:** Golden Config is a plugin, not core Nautobot. Its API structure differs from core API. Plugin version may not match docs.
**Prevention:** Discover actual installed plugin version via API. Test against real Golden Config endpoints on user's server. Don't assume plugin API follows core patterns.
**Phase:** Phase 3 (Golden Config integration)

## Moderate Pitfalls

### 7. MCP Server Startup/Registration
**Warning signs:** Agent can't find tools, connection refused
**What goes wrong:** MCP servers need proper stdio/SSE transport setup. Misconfigured transport means agents can't discover tools.
**Prevention:** Use FastMCP's built-in transport handling. Test with a real MCP client (Claude, etc.) early in development. Provide clear setup instructions.
**Phase:** Phase 2 (MCP server)

### 8. Idempotency in Data Operations
**Warning signs:** Duplicate objects in Nautobot, update vs create confusion
**What goes wrong:** Running onboarding twice creates duplicate interfaces, IPs, etc.
**Prevention:** Always check existence before creating. Use natural keys (device name + interface name) for lookups. Implement update-or-create pattern with pynautobot's `get()` + `create()`.
**Phase:** Phase 1-2 (Core client + onboarding)

### 9. Error Handling for AI Agents
**Warning signs:** Agent gets confused by errors, retries infinitely, makes wrong decisions
**What goes wrong:** Generic error messages ("request failed") don't help agents decide what to do next. Stack traces are useless to LLMs.
**Prevention:** Return structured error responses with: what failed, why, what the agent should try instead. Use MCP's error protocol properly.
**Phase:** Phase 2 (MCP server)

### 10. Testing Without a Real Nautobot
**Warning signs:** Tests pass but tool breaks in production
**What goes wrong:** Mocking Nautobot API hides real-world issues (pagination, auth, nested objects).
**Prevention:** Use a combination of unit tests (mocked) and integration tests (against real/sandbox Nautobot). Maintain test fixtures from actual API responses.
**Phase:** All phases
