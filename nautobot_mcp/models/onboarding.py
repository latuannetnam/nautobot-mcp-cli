"""Pydantic models for config onboarding operations.

Models represent planned changes (actions) and results of onboarding
a parsed device configuration into Nautobot.
"""

from __future__ import annotations

from pydantic import BaseModel


class OnboardAction(BaseModel):
    """Single planned change during onboarding.

    Represents one object that will be created, updated, or skipped
    when onboarding a parsed config into Nautobot.
    """

    action: str  # "create", "update", "skip"
    object_type: str  # "device", "interface", "ip_address", "prefix", "vlan"
    name: str  # object identifier (e.g., "ge-0/0/0", "10.0.0.1/30")
    details: dict = {}  # what will be created/changed
    reason: str = ""  # why (e.g., "not found in Nautobot", "description changed")


class OnboardSummary(BaseModel):
    """Summary counts of onboarding actions by type."""

    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


class OnboardResult(BaseModel):
    """Full result of an onboarding operation.

    Contains the device name, mode (dry-run or commit), summary counts,
    detailed actions list, and any warnings encountered.
    """

    device: str
    dry_run: bool = True
    summary: OnboardSummary = OnboardSummary()
    actions: list[OnboardAction] = []
    warnings: list[str] = []
