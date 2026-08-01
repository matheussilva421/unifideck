"""Phase 2B: Canonical Form includes the Command Placeholder.

New shortcuts and force-synced shortcuts write
``%command% <store>:<id>`` instead of the bare token.
``_reclaim_orphan`` must keep receiving the pure token so
``preserve_user_params`` doesn't inject ``%command%`` mid-string.
"""
from __future__ import annotations

from typing import Any

from unifideck.services.shortcut.launch_options import (
    canonical_launch_options,
    get_full_id,
    preserve_user_params,
)
from unifideck.services.shortcut.reconcile_helpers import build_launch_index


class _FakeGame:
    def __init__(self, store: str = "epic", game_id: str = "123") -> None:
        self.store = store
        self.store_game_id = game_id
        self.title = "Test Game"
        self.icon_url = ""
        self.install_path = "/games/test"
        self.installed = True


class _FakeReconciler:
    _launcher_path = "/home/deck/homebrew/plugins/Unifideck/bin/unifideck-launcher"

    from unifideck.services.shortcut.reconcile_phases import (
        _ReconcilePhasesMixin,
    )

    _reclaim_orphan = _ReconcilePhasesMixin._reclaim_orphan
    _build_shortcut_entry = _ReconcilePhasesMixin._build_shortcut_entry
    _update_existing_shortcut = _ReconcilePhasesMixin._update_existing_shortcut


def test_canonical_launch_options_format():
    assert canonical_launch_options("epic", "123") == "%command% epic:123"
    assert canonical_launch_options("gog", "1103900211") == "%command% gog:1103900211"


def test_new_shortcut_has_command_placeholder():
    r = _FakeReconciler()
    entry = r._build_shortcut_entry(_FakeGame(), app_id=42)
    assert entry["LaunchOptions"] == "%command% epic:123"


def test_force_sync_writes_command_placeholder():
    r = _FakeReconciler()
    entry: dict[str, Any] = {
        "appid": 42,
        "AppName": "Old",
        "Exe": '""',
        "LaunchOptions": "epic:123",
        "tags": {},
    }
    r._update_existing_shortcut(entry, _FakeGame(), app_id=42, launcher="/bin/launcher")
    assert entry["LaunchOptions"] == "%command% epic:123"


def test_get_full_id_tolerates_command_placeholder():
    assert get_full_id("%command% epic:123") == "epic:123"
    assert get_full_id("MANGOHUD=1 %command% epic:123") == "epic:123"


def test_build_launch_index_indexes_command_placeholder():
    shortcuts = {
        "0": {"LaunchOptions": "%command% epic:123", "appid": 42},
        "1": {"LaunchOptions": "gog:456", "appid": 43},
    }
    index = build_launch_index(shortcuts)
    assert index["epic:123"] == "0"
    assert index["gog:456"] == "1"


def test_reclaim_orphan_does_not_inject_placeholder():
    """_reclaim_orphan must pass the pure token to preserve_user_params.

    If it passed the canonical form (with %command%), the placeholder
    would be injected in the middle of the user's string.
    """
    r = _FakeReconciler()
    entry: dict[str, Any] = {
        "appid": 99,
        "AppName": "Orphan",
        "Exe": '"/old/launcher"',
        "LaunchOptions": "FOO=1 epic:999 BAR=2",
        "icon": "",
        "tags": {},
    }
    r._reclaim_orphan(entry, _FakeGame(store="epic", game_id="123"), app_id=99)
    assert entry["LaunchOptions"] == "FOO=1 epic:123 BAR=2"
    assert "%command%" not in entry["LaunchOptions"]


def test_preserve_user_params_pure_token():
    result = preserve_user_params("FOO=1 epic:999 BAR=2", "epic:123")
    assert result == "FOO=1 epic:123 BAR=2"
