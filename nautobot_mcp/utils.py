"""Shared utility helpers for bulk API operations."""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")


def chunked(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Split an iterable into chunks of at most `size` items.

    Args:
        iterable: Any iterable (list, tuple, etc.).
        size: Maximum chunk size.

    Yields:
        Lists of at most `size` items from the input.
    """
    it = iter(iterable)
    while chunk := list(itertools.islice(it, size)):
        yield chunk


def group_by_attr(items: list, attr: str) -> dict:
    """Group a list of objects by a common attribute.

    Args:
        items: List of objects (pydantic models, dataclasses, dicts).
        attr: Attribute name to group by.

    Returns:
        Dict mapping attr value → list of items with that attr value.
    """
    result: dict = {}
    for item in items:
        key = getattr(item, attr, None)
        if key is not None:
            result.setdefault(key, []).append(item)
    return result
