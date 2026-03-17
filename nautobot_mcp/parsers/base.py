"""Abstract base class and registry for vendor config parsers.

Provides VendorParser ABC that all vendor parsers must implement,
and ParserRegistry for discovering parsers by network_os identifier.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from nautobot_mcp.models.parser import ParsedConfig


class VendorParser(ABC):
    """Abstract base class for vendor config parsers.

    Subclasses must implement parse() and register via ParserRegistry.
    Identifier should match netutils network_os (e.g., "juniper_junos").
    """

    @property
    @abstractmethod
    def network_os(self) -> str:
        """netutils-compatible platform identifier."""
        ...

    @property
    @abstractmethod
    def vendor(self) -> str:
        """Vendor name (e.g., 'juniper')."""
        ...

    @abstractmethod
    def parse(self, config_data: dict | str) -> ParsedConfig:
        """Parse device config and return structured ParsedConfig.

        Args:
            config_data: JSON dict from 'show configuration | display json'
                         or raw text config string

        Returns:
            ParsedConfig with all extracted data and warnings for skipped sections
        """
        ...

    @abstractmethod
    def detect_platform(self, config_data: dict) -> str:
        """Auto-detect platform variant from config data.

        Returns platform hint string (e.g., "MX", "EX", "SRX").
        """
        ...


class ParserRegistry:
    """Registry for vendor parsers. Keyed by network_os identifier."""

    _parsers: dict[str, type[VendorParser]] = {}

    @classmethod
    def register(cls, parser_class: type[VendorParser]) -> type[VendorParser]:
        """Register a parser class. Can be used as decorator."""
        instance = parser_class()
        cls._parsers[instance.network_os] = parser_class
        return parser_class

    @classmethod
    def get(cls, network_os: str) -> VendorParser:
        """Get a parser instance by network_os identifier.

        Raises ValueError if no parser registered for that network_os.
        """
        if network_os not in cls._parsers:
            available = ", ".join(cls._parsers.keys()) or "none"
            raise ValueError(
                f"No parser registered for network_os='{network_os}'. "
                f"Available parsers: {available}"
            )
        return cls._parsers[network_os]()

    @classmethod
    def list_parsers(cls) -> list[str]:
        """Return list of registered network_os identifiers."""
        return list(cls._parsers.keys())
