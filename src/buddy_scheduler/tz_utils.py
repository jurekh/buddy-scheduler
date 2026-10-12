"""Timezone string similarity utility.

Compatibility is assessed by string similarity, not UTC-offset arithmetic,
consistent with the project assumption that timezone designations are free-form
strings (e.g. "UTC+1", "America/New_York", "EMEA").
"""

from __future__ import annotations

import difflib


def tz_penalty(tz_a: str, tz_b: str) -> float:
    """Return a penalty in [0, 1] reflecting timezone incompatibility.

    A penalty of ``0.0`` means the two timezone strings are identical.
    A penalty of ``1.0`` means they share no common characters.
    An empty timezone string is treated as fully incompatible (penalty ``1.0``).

    Args:
        tz_a: First timezone string.
        tz_b: Second timezone string.

    Returns:
        ``1.0 - SequenceMatcher.ratio(tz_a.strip(), tz_b.strip())``.
    """
    a = tz_a.strip()
    b = tz_b.strip()
    if not a or not b:
        return 1.0
    return 1.0 - difflib.SequenceMatcher(None, a, b).ratio()
