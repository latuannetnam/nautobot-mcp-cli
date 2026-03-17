"""Golden Config domain operations using the Nautobot API client.

Provides config retrieval, compliance features/rules CRUD, compliance
result retrieval, and quick diff operations for the Golden Config plugin.
"""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING, Optional

from nautobot_mcp.exceptions import NautobotNotFoundError
from nautobot_mcp.models.base import ListResponse
from nautobot_mcp.models.golden_config import (
    ComplianceFeatureResult,
    ComplianceFeatureSummary,
    ComplianceResult,
    ComplianceRuleSummary,
    ConfigDiff,
    GoldenConfigEntry,
)

if TYPE_CHECKING:
    from nautobot_mcp.client import NautobotClient


# ---------------------------------------------------------------------------
# Config Retrieval (GC-01, GC-02)
# ---------------------------------------------------------------------------


def get_intended_config(
    client: NautobotClient,
    device_name_or_id: str,
) -> GoldenConfigEntry:
    """Retrieve the intended (golden) configuration for a device.

    Args:
        client: NautobotClient instance.
        device_name_or_id: Device name or UUID.

    Returns:
        GoldenConfigEntry with intended_config populated.
    """
    try:
        configs = list(
            client.golden_config.golden_config.filter(device=device_name_or_id)
        )
        if not configs:
            raise NautobotNotFoundError(
                message=f"No Golden Config entry found for device '{device_name_or_id}'",
                hint="Ensure the device has an intended config generated in Golden Config",
            )
        return GoldenConfigEntry.from_nautobot(configs[0])
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get_intended_config", "GoldenConfig")
        raise


def get_backup_config(
    client: NautobotClient,
    device_name_or_id: str,
) -> GoldenConfigEntry:
    """Retrieve the backup configuration for a device.

    Args:
        client: NautobotClient instance.
        device_name_or_id: Device name or UUID.

    Returns:
        GoldenConfigEntry with backup_config populated.
    """
    try:
        configs = list(
            client.golden_config.golden_config.filter(device=device_name_or_id)
        )
        if not configs:
            raise NautobotNotFoundError(
                message=f"No Golden Config entry found for device '{device_name_or_id}'",
                hint="Ensure the device has a backup config collected in Golden Config",
            )
        return GoldenConfigEntry.from_nautobot(configs[0])
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get_backup_config", "GoldenConfig")
        raise


# ---------------------------------------------------------------------------
# Compliance Features CRUD (GC-03)
# ---------------------------------------------------------------------------


def list_compliance_features(
    client: NautobotClient,
) -> ListResponse[ComplianceFeatureSummary]:
    """List all compliance features.

    Args:
        client: NautobotClient instance.

    Returns:
        ListResponse with count and ComplianceFeatureSummary results.
    """
    try:
        features = list(client.golden_config.compliance_feature.all())
        results = [ComplianceFeatureSummary.from_nautobot(f) for f in features]
        return ListResponse(count=len(results), results=results)
    except Exception as e:
        client._handle_api_error(e, "list", "ComplianceFeature")
        raise


def create_compliance_feature(
    client: NautobotClient,
    name: str,
    slug: str,
    description: str = "",
) -> ComplianceFeatureSummary:
    """Create a new compliance feature.

    Args:
        client: NautobotClient instance.
        name: Feature name.
        slug: Feature slug.
        description: Optional description.

    Returns:
        ComplianceFeatureSummary for the created feature.
    """
    try:
        feature = client.golden_config.compliance_feature.create(
            name=name,
            slug=slug,
            description=description,
        )
        return ComplianceFeatureSummary.from_nautobot(feature)
    except Exception as e:
        client._handle_api_error(e, "create", "ComplianceFeature")
        raise


def delete_compliance_feature(
    client: NautobotClient,
    feature_id: str,
) -> dict:
    """Delete a compliance feature by ID.

    Args:
        client: NautobotClient instance.
        feature_id: UUID of the compliance feature to delete.

    Returns:
        Dict with success status and message.
    """
    try:
        feature = client.golden_config.compliance_feature.get(id=feature_id)
        if feature is None:
            raise NautobotNotFoundError(
                message=f"Compliance feature '{feature_id}' not found",
            )
        feature.delete()
        return {"success": True, "message": f"Compliance feature {feature_id} deleted"}
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "delete", "ComplianceFeature")
        raise


# ---------------------------------------------------------------------------
# Compliance Rules CRUD (GC-04)
# ---------------------------------------------------------------------------


def list_compliance_rules(
    client: NautobotClient,
    feature: Optional[str] = None,
    platform: Optional[str] = None,
) -> ListResponse[ComplianceRuleSummary]:
    """List compliance rules with optional filtering.

    Args:
        client: NautobotClient instance.
        feature: Filter by feature name.
        platform: Filter by platform slug.

    Returns:
        ListResponse with count and ComplianceRuleSummary results.
    """
    try:
        filters = {}
        if feature:
            filters["feature"] = feature
        if platform:
            filters["platform"] = platform

        if filters:
            rules = list(client.golden_config.compliance_rule.filter(**filters))
        else:
            rules = list(client.golden_config.compliance_rule.all())

        results = [ComplianceRuleSummary.from_nautobot(r) for r in rules]
        return ListResponse(count=len(results), results=results)
    except Exception as e:
        client._handle_api_error(e, "list", "ComplianceRule")
        raise


def create_compliance_rule(
    client: NautobotClient,
    feature: str,
    platform: str,
    config_ordered: bool = False,
    match_config: str = "",
    description: str = "",
) -> ComplianceRuleSummary:
    """Create a new compliance rule.

    Args:
        client: NautobotClient instance.
        feature: Feature name to associate.
        platform: Platform slug.
        config_ordered: Whether config order matters.
        match_config: Regex/pattern to match config sections.
        description: Optional description.

    Returns:
        ComplianceRuleSummary for the created rule.
    """
    try:
        rule = client.golden_config.compliance_rule.create(
            feature=feature,
            platform=platform,
            config_ordered=config_ordered,
            match_config=match_config,
            description=description,
        )
        return ComplianceRuleSummary.from_nautobot(rule)
    except Exception as e:
        client._handle_api_error(e, "create", "ComplianceRule")
        raise


def update_compliance_rule(
    client: NautobotClient,
    rule_id: str,
    **updates,
) -> ComplianceRuleSummary:
    """Update an existing compliance rule.

    Args:
        client: NautobotClient instance.
        rule_id: UUID of the rule to update.
        **updates: Fields to update.

    Returns:
        ComplianceRuleSummary for the updated rule.
    """
    try:
        rule = client.golden_config.compliance_rule.get(id=rule_id)
        if rule is None:
            raise NautobotNotFoundError(
                message=f"Compliance rule '{rule_id}' not found for update",
                hint="Verify the rule ID exists",
            )
        for key, value in updates.items():
            setattr(rule, key, value)
        rule.save()
        return ComplianceRuleSummary.from_nautobot(rule)
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "update", "ComplianceRule")
        raise


def delete_compliance_rule(
    client: NautobotClient,
    rule_id: str,
) -> dict:
    """Delete a compliance rule by ID.

    Args:
        client: NautobotClient instance.
        rule_id: UUID of the compliance rule to delete.

    Returns:
        Dict with success status and message.
    """
    try:
        rule = client.golden_config.compliance_rule.get(id=rule_id)
        if rule is None:
            raise NautobotNotFoundError(
                message=f"Compliance rule '{rule_id}' not found",
            )
        rule.delete()
        return {"success": True, "message": f"Compliance rule {rule_id} deleted"}
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "delete", "ComplianceRule")
        raise


# ---------------------------------------------------------------------------
# Compliance Checks (GC-05, GC-06)
# ---------------------------------------------------------------------------


def get_compliance_results(
    client: NautobotClient,
    device_name_or_id: str,
) -> ComplianceResult:
    """Get compliance results for a device from the server.

    Args:
        client: NautobotClient instance.
        device_name_or_id: Device name or UUID.

    Returns:
        ComplianceResult with per-feature compliance status.
    """
    try:
        results = list(
            client.golden_config.config_compliance.filter(device=device_name_or_id)
        )
        if not results:
            raise NautobotNotFoundError(
                message=f"No compliance results found for device '{device_name_or_id}'",
                hint="Run a compliance check first, or verify the device name",
            )
        return ComplianceResult.from_nautobot(device_name_or_id, results)
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "get_compliance_results", "ConfigCompliance")
        raise


def quick_diff_config(
    client: NautobotClient,
    device_name_or_id: str,
) -> ComplianceResult:
    """Quick diff intended vs backup config for a device.

    Pulls both configs and uses difflib to find differences,
    returning a ComplianceResult with source="quick-diff".

    Args:
        client: NautobotClient instance.
        device_name_or_id: Device name or UUID.

    Returns:
        ComplianceResult with diff-based compliance status.
    """
    try:
        entry = get_intended_config(client, device_name_or_id)
        intended = entry.intended_config
        backup = entry.backup_config

        if not intended and not backup:
            return ComplianceResult(
                device=device_name_or_id,
                overall_status="pending",
                source="quick-diff",
            )

        intended_lines = intended.splitlines(keepends=True)
        backup_lines = backup.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                backup_lines,
                intended_lines,
                fromfile="backup",
                tofile="intended",
                lineterm="",
            )
        )

        added = [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]
        removed = [line[1:] for line in diff if line.startswith("-") and not line.startswith("---")]
        context = [line[1:] for line in diff if line.startswith(" ")]

        if not added and not removed:
            status = "compliant"
        else:
            status = "non-compliant"

        features = [
            ComplianceFeatureResult(
                feature="full-config",
                status=status,
                missing_lines="\n".join(added),
                extra_lines="\n".join(removed),
                actual=backup,
                intended=intended,
            )
        ]

        return ComplianceResult(
            device=device_name_or_id,
            overall_status=status,
            features=features,
            source="quick-diff",
        )
    except NautobotNotFoundError:
        raise
    except Exception as e:
        client._handle_api_error(e, "quick_diff_config", "GoldenConfig")
        raise
