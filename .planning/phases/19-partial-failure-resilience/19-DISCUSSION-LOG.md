# Phase 19: Partial Failure Resilience - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 19-partial-failure-resilience
**Areas discussed:** Warning Accumulation Pattern, Partial Status Semantics, Degradation Boundary, Envelope Shape Change

---

## Warning Accumulation Pattern

### Q1: Warning format
| Option | Description | Selected |
|--------|-------------|----------|
| Operation + error message | `{"operation": "...", "error": "..."}` | ✓ |
| Operation + error + fallback | Adds `"fallback": []` to each warning | |
| You decide | Agent discretion | |

**User's choice:** Operation + error message (1a)

### Q2: Accumulation scope
| Option | Description | Selected |
|--------|-------------|----------|
| Single flat list | One list for the whole composite call | ✓ |
| Nested per-section | Warnings grouped by section | |
| You decide | Agent discretion | |

**User's choice:** Single flat list (2a)

### Q3: Inner try/except upgrade scope
| Option | Description | Selected |
|--------|-------------|----------|
| All existing silent try/excepts | Comprehensive — ~15 locations across 4 files | ✓ |
| Only composite summary functions | Targeted — matches PFR scope | |
| You decide | Agent discretion | |

**User's choice:** All existing silent try/excepts (3a)

### Q4: Logging
| Option | Description | Selected |
|--------|-------------|----------|
| Yes — log + return | Warnings logged via logger.warning() and returned in envelope | ✓ |
| No — return only | Only returned in envelope | |
| You decide | Agent discretion | |

**User's choice:** Yes — log + return (4a)

---

## Partial Status Semantics

### Q1: Status determination rule
| Option | Description | Selected |
|--------|-------------|----------|
| Primary fail → error; enrichment fail → partial | Simple universal rule | ✓ |
| Threshold-based | Majority fail → error; minority → partial | |
| You decide | Agent discretion | |

**User's choice:** Primary fail → error; enrichment fail → partial (1a)

### Q2: Backward compatibility
| Option | Description | Selected |
|--------|-------------|----------|
| Accept breaking change | Agents update for v1.4 | ✓ |
| Add is_complete boolean | Gradual migration | |
| You decide | Agent discretion | |

**User's choice:** Accept breaking change (2a)

### Q3: Error field behavior when partial
| Option | Description | Selected |
|--------|-------------|----------|
| null — details in warnings only | error = fatal, warnings = degraded | |
| Summary string | e.g., "2 of 4 enrichment queries failed" | ✓ |
| You decide | Agent discretion | |

**User's choice:** Summary string (3b)

---

## Degradation Boundary

### Q1: Universal rule vs per-workflow config
| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded per-function | Developer marks each call site | ✓ |
| Configurable in registry | primary_ops and enrichment_ops lists | |
| You decide | Agent discretion | |

**User's choice:** Hardcoded per-function (1a)

### Q2: Multiple primary queries (firewall)
| Option | Description | Selected |
|--------|-------------|----------|
| Partial — return whatever succeeded | Independent co-primaries | ✓ |
| Error — any primary fails = total fail | All-or-nothing for primaries | |
| You decide | Agent discretion | |

**User's choice:** Partial — filters and policers are co-equal Juniper features, treat as independent co-primaries (2a, with user context)
**Notes:** User clarified that filters and policers are two major features of Juniper Firewall — they should be treated as independent co-primaries. Only if BOTH fail should status be error.

### Q3: interface_detail per-unit failures
| Option | Description | Selected |
|--------|-------------|----------|
| Partial — include succeeded units, warn about failures | Granular per-unit | ✓ |
| Partial — all units but empty data for failed ones | Include all, empty fallback | |
| You decide | Agent discretion | |

**User's choice:** Include units that succeeded, warn about failed units (3a)

---

## Envelope Shape Change

### Q1: Envelope structure
| Option | Description | Selected |
|--------|-------------|----------|
| Always present as [] | Consistent for agents | ✓ |
| Only when non-empty | Omitted when ok | |
| You decide | Agent discretion | |

**User's choice:** Always present as [] (1a)

### Q2: Warning object shape
| Option | Description | Selected |
|--------|-------------|----------|
| operation + error | Matches Area 1 decision | ✓ |
| operation + error + child_index | Adds position in sequence | |
| You decide | Agent discretion | |

**User's choice:** operation + error (2a)

### Q3: Composite function return type
| Option | Description | Selected |
|--------|-------------|----------|
| Return tuple (result, warnings) | Explicit, no side effects | ✓ |
| Attach to result object | Less clean, no signature change | |
| You decide | Agent discretion | |

**User's choice:** Return tuple (result, warnings) (3a)

---

## Agent's Discretion

- WarningCollector class implementation details (dataclass vs regular class)
- Logger format for warning messages
- Test structure and organization

## Deferred Ideas

None — discussion stayed within phase scope
