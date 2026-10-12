"""Unit tests for the timezone string similarity utility."""

from __future__ import annotations

import pytest

from buddy_scheduler.tz_utils import tz_penalty


class TestTzPenalty:
    """T024: Timezone penalty edge cases and expected behaviours."""

    def test_identical_strings_returns_zero(self) -> None:
        assert tz_penalty("UTC", "UTC") == pytest.approx(0.0)

    def test_identical_complex_strings_returns_zero(self) -> None:
        assert tz_penalty("America/New_York", "America/New_York") == pytest.approx(0.0)

    def test_empty_first_string_returns_one(self) -> None:
        assert tz_penalty("", "UTC") == pytest.approx(1.0)

    def test_empty_second_string_returns_one(self) -> None:
        assert tz_penalty("UTC", "") == pytest.approx(1.0)

    def test_both_empty_returns_one(self) -> None:
        assert tz_penalty("", "") == pytest.approx(1.0)

    def test_whitespace_only_treated_as_empty(self) -> None:
        assert tz_penalty("  ", "UTC") == pytest.approx(1.0)

    def test_penalty_in_range(self) -> None:
        p = tz_penalty("America/New_York", "Europe/London")
        assert 0.0 <= p <= 1.0

    def test_partial_match_between_zero_and_one(self) -> None:
        p = tz_penalty("UTC+1", "UTC+2")
        assert 0.0 < p < 1.0

    def test_completely_different_strings_close_to_one(self) -> None:
        p = tz_penalty("AAAAAA", "ZZZZZZ")
        assert p > 0.5

    def test_case_sensitive(self) -> None:
        p_same = tz_penalty("utc", "utc")
        p_mixed = tz_penalty("UTC", "utc")
        assert p_same == pytest.approx(0.0)
        assert p_mixed > 0.0

    def test_leading_trailing_whitespace_stripped(self) -> None:
        assert tz_penalty("  UTC  ", "UTC") == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "tz",
        [
            "America/New_York",
            "UTC+1",
            "EMEA",
            "BST",
            "Europe/London",
            "Asia/Tokyo",
        ],
    )
    def test_same_timezone_always_zero(self, tz: str) -> None:
        assert tz_penalty(tz, tz) == pytest.approx(0.0)

    def test_symmetry(self) -> None:
        assert tz_penalty("UTC+1", "America/New_York") == pytest.approx(
            tz_penalty("America/New_York", "UTC+1")
        )
