"""Pydantic models for CMS plugin (netnam-cms-core) data objects.

Submodules per domain are added in subsequent phases:
- routing.py (Phase 9)
- interfaces.py (Phase 10)
- firewalls.py (Phase 11)
- policies.py (Phase 11)
- arp.py (Phase 12)
"""

from nautobot_mcp.models.cms.base import CMSBaseSummary

__all__ = [
    "CMSBaseSummary",
]
