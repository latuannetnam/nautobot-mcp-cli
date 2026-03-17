"""Pydantic models for Golden Config plugin data.

Models represent Nautobot Golden Config objects (compliance features,
rules, config entries, and compliance results) with from_nautobot()
factory methods for conversion from pynautobot records.
"""

from __future__ import annotations

from pydantic import BaseModel


class ComplianceFeatureSummary(BaseModel):
    """Compliance feature label for grouping rules."""

    id: str
    name: str
    slug: str
    description: str = ""

    @classmethod
    def from_nautobot(cls, nb_record) -> "ComplianceFeatureSummary":
        return cls(
            id=str(nb_record.id),
            name=nb_record.name,
            slug=nb_record.slug,
            description=getattr(nb_record, "description", "") or "",
        )


class ComplianceRuleSummary(BaseModel):
    """Compliance rule linking a feature to a platform."""

    id: str
    feature: str  # feature name
    platform: str  # platform slug
    config_ordered: bool = False
    config_remediation: bool = False
    match_config: str = ""
    description: str = ""

    @classmethod
    def from_nautobot(cls, nb_record) -> "ComplianceRuleSummary":
        return cls(
            id=str(nb_record.id),
            feature=str(nb_record.feature),
            platform=str(nb_record.platform),
            config_ordered=getattr(nb_record, "config_ordered", False),
            config_remediation=getattr(nb_record, "config_remediation", False),
            match_config=getattr(nb_record, "match_config", "") or "",
            description=getattr(nb_record, "description", "") or "",
        )


class GoldenConfigEntry(BaseModel):
    """Intended/backup configuration for a device."""

    id: str
    device: str
    device_id: str
    intended_config: str = ""
    backup_config: str = ""
    compliance_config: str = ""

    @classmethod
    def from_nautobot(cls, nb_record) -> "GoldenConfigEntry":
        return cls(
            id=str(nb_record.id),
            device=str(nb_record.device),
            device_id=str(getattr(nb_record.device, "id", "")),
            intended_config=getattr(nb_record, "intended_config", "") or "",
            backup_config=getattr(nb_record, "backup_config", "") or "",
            compliance_config=getattr(nb_record, "compliance_config", "") or "",
        )


class ComplianceFeatureResult(BaseModel):
    """Per-feature compliance result."""

    feature: str
    status: str  # "compliant" or "non-compliant"
    ordered: bool = False
    missing_lines: str = ""
    extra_lines: str = ""
    actual: str = ""
    intended: str = ""


class ComplianceResult(BaseModel):
    """Full compliance report for a device."""

    device: str
    overall_status: str  # "compliant", "non-compliant", "pending"
    features: list[ComplianceFeatureResult] = []
    checked_at: str = ""
    source: str = ""  # "server" or "quick-diff"

    @classmethod
    def from_nautobot(cls, device_name: str, nb_records) -> "ComplianceResult":
        features = []
        for r in nb_records:
            features.append(
                ComplianceFeatureResult(
                    feature=str(r.feature),
                    status="compliant" if r.compliance else "non-compliant",
                    ordered=getattr(r, "ordered", False),
                    missing_lines=getattr(r, "missing", "") or "",
                    extra_lines=getattr(r, "extra", "") or "",
                    actual=getattr(r, "actual", "") or "",
                    intended=getattr(r, "intended", "") or "",
                )
            )
        overall = (
            "compliant"
            if all(f.status == "compliant" for f in features)
            else "non-compliant"
        )
        return cls(
            device=device_name,
            overall_status=overall,
            features=features,
            source="server",
        )


class ConfigDiff(BaseModel):
    """Quick diff result for a config section."""

    section: str
    added_lines: list[str] = []
    removed_lines: list[str] = []
    context_lines: list[str] = []
