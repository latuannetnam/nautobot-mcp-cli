"""CMS Plugin domain operations for Juniper network models.

Provides CRUD operations for all netnam-cms-core plugin models:
- Routing: Static routes, BGP groups/neighbors/address families
- Interfaces: Interface units, families, VRRP
- Firewalls: Filters, terms, policers, match conditions
- Policies: Policy statements, JPS terms/matches/actions
- ARP: ARP entries
"""

from nautobot_mcp.cms import arp  # noqa: F401
from nautobot_mcp.cms import interfaces  # noqa: F401
from nautobot_mcp.cms import routing  # noqa: F401

__all__ = ["routing", "interfaces", "arp"]

