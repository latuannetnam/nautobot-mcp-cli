"""Warning collector for partial failure resilience in composite workflows."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WarningCollector:
    """Accumulates per-child-call warnings during composite workflow execution.

    Each composite function receives a WarningCollector instance, adds warnings
    for any failed enrichment queries, and returns it alongside the result.
    The dispatch engine extracts warnings and includes them in the response envelope.

    Usage:
        collector = WarningCollector()
        try:
            data = fetch_enrichment(...)
        except Exception as e:
            collector.add("fetch_enrichment", str(e))
            data = []  # fallback
        return result, collector.warnings
    """

    _warnings: list[dict[str, str]] = field(default_factory=list)

    def add(self, operation: str, error: str) -> None:
        """Record a warning for a failed child operation.

        Also emits a logger.warning() for server-side observability.

        Args:
            operation: Name of the failed operation (e.g., "list_bgp_address_families").
            error: Error message string.
        """
        logger.warning("Partial failure in %s: %s", operation, error)
        self._warnings.append({"operation": operation, "error": error})

    @property
    def warnings(self) -> list[dict[str, str]]:
        """Return accumulated warnings as a list of dicts."""
        return list(self._warnings)

    @property
    def has_warnings(self) -> bool:
        """Return True if any warnings have been recorded."""
        return len(self._warnings) > 0

    def summary(self, total_ops: int) -> str:
        """Generate a summary string for the envelope error field.

        Args:
            total_ops: Total number of enrichment operations attempted.

        Returns:
            Summary like "2 of 4 enrichment queries failed".
        """
        count = len(self._warnings)
        return f"{count} of {total_ops} enrichment queries failed"
