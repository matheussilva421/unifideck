"""Phase 2C: reorder() — pure Launch Options reordering.

reorder() detects Broken Ordering and returns the Canonical Form,
or None if the string is already healthy. It reorders and NEVER
redacts: the multiset of tokens in the output equals the input
plus at most one %command%.
"""
from __future__ import annotations

import shlex

import pytest

from unifideck.services.shortcut.reordering import reorder


class TestReorderTable:
    @pytest.mark.parametrize(
        ("input_", "expected"),
        [
            ("epic:123", "%command% epic:123"),
            ("ENV=1 epic:123 %command%", "ENV=1 %command% epic:123"),
            ("ENV=1 epic:123", "ENV=1 %command% epic:123"),
            ("%command% ENV=1 epic:123", "ENV=1 %command% epic:123"),
            ("ENV=1 %command% epic:123", None),
            ("%command% epic:123", None),
        ],
    )
    def test_table(self, input_: str, expected: str | None):
        assert reorder(input_) == expected


class TestPreservation:
    """The multiset of tokens in the output equals the input plus at most one %command%."""

    def _token_multiset(self, s: str) -> dict[str, int]:
        try:
            tokens = shlex.split(s)
        except ValueError:
            tokens = s.split()
        counts: dict[str, int] = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1
        return counts

    @pytest.mark.parametrize(
        "input_",
        [
            "epic:123",
            "ENV=1 epic:123 %command%",
            "ENV=1 epic:123",
            "%command% ENV=1 epic:123",
            'PROTON_REMOTE_DEBUG_CMD="/home/deck/Games/Trainers/trainer.exe" PRESSURE_VESSEL_FILESYSTEMS_RW="/home/deck/Games/Trainers" epic:abc123 %command%',
            'PROTON_REMOTE_DEBUG_CMD="/home/deck/Games/Trainers/Crysis Remastered/trainer.exe" PRESSURE_VESSEL_FILESYSTEMS_RW="/home/deck/Games/Trainers/Crysis Remastered" %command% epic:52b99f5f12964e89b5e3e0a978e8c5f5',
        ],
    )
    def test_no_tokens_lost_or_invented(self, input_: str):
        result = reorder(input_)
        if result is None:
            return
        in_counts = self._token_multiset(input_)
        out_counts = self._token_multiset(result)
        cmd_delta = out_counts.get("%command%", 0) - in_counts.get("%command%", 0)
        assert cmd_delta in (0, 1), "at most one %command% may be added"
        if cmd_delta == 1:
            out_counts = dict(out_counts)
            out_counts["%command%"] = out_counts.get("%command%", 1) - 1
            if out_counts["%command%"] == 0:
                del out_counts["%command%"]
        assert in_counts == out_counts, (
            f"token multiset mismatch:\n  in={in_counts}\n  out={out_counts}"
        )

    def test_quoted_values_with_internal_spaces(self):
        input_ = 'WINEDLLOVERRIDES="dxgi=n,b" %command% epic:123'
        assert reorder(input_) is None

    def test_quoted_value_moved_preserves_quotes(self):
        input_ = 'FOO="bar baz" epic:123 %command%'
        result = reorder(input_)
        assert result is not None
        assert '"bar baz"' in result


class TestIdempotency:
    @pytest.mark.parametrize(
        "input_",
        [
            "epic:123",
            "ENV=1 epic:123 %command%",
            "%command% ENV=1 epic:123",
            "ENV=1 epic:123",
        ],
    )
    def test_reorder_of_reorder_is_none(self, input_: str):
        first = reorder(input_)
        if first is None:
            return
        assert reorder(first) is None


class TestEdgeCases:
    def test_empty_string(self):
        assert reorder("") is None

    def test_only_command_placeholder(self):
        assert reorder("%command%") is None

    def test_no_store_token(self):
        assert reorder("MANGOHUD=1 %command%") is None

    def test_multiple_command_placeholders(self):
        result = reorder("%command% %command% epic:123")
        assert result is not None
        assert result.count("%command%") == 1

    def test_env_after_placeholder_moved_before(self):
        assert reorder("%command% MANGOHUD=1 epic:123") == "MANGOHUD=1 %command% epic:123"
