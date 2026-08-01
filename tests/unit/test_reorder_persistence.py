"""The reorder pass must survive a sync that changes nothing else.

``reconcile`` only writes ``shortcuts.vdf`` when something was added,
removed or reclaimed. A shortcut broken by CheatDeck is none of those —
it is *kept* — so a reorder applied during a steady-state sync was
computed in memory and thrown away.

That is precisely the scenario the feature exists for: the library is
stable, CheatDeck mangles one shortcut's LaunchOptions, the user syncs
to repair it, and nothing is added or removed.
"""
from __future__ import annotations

import pytest

from unifideck.services.shortcut.games_map import UNIFIDECK_TAG
from unifideck.services.shortcut.reconcile_phases import _ReconcilePhasesMixin

_LAUNCHER = "/home/deck/homebrew/plugins/Unifideck/bin/unifideck-launcher"


class _Game:
    def __init__(self, store: str = "epic", game_id: str = "123") -> None:
        self.store = store
        self.store_game_id = game_id
        self.title = "Test Game"
        self.icon_url = ""
        self.install_path = "/games/test"
        self.installed = True
        self.app_id = 4242
        self.exe_path = "/games/test/game.exe"


class _Reconciler(_ReconcilePhasesMixin):
    """Minimal host for the mixin, tracking whether a save happened."""

    def __init__(self, launch_options: str) -> None:
        self._launcher_path = _LAUNCHER
        self._shortcuts = {
            "shortcuts": {
                "0": {
                    "appid": 4242,
                    "AppName": "Test Game",
                    "Exe": f'"{_LAUNCHER}"',
                    "LaunchOptions": launch_options,
                    "tags": {"0": UNIFIDECK_TAG, "1": "epic", "2": ""},
                },
            },
        }
        self._games_map: dict = {}
        self.saved = False

    async def _load_shortcuts(self) -> None: ...
    async def _load_games_map(self) -> None: ...
    async def _reset_lastplaytime_once(self) -> None: ...

    async def _save_all(self) -> None:
        self.saved = True

    def _find_existing_shortcut_key(self, shortcuts_dict, app_id):
        for key, entry in shortcuts_dict.items():
            if entry.get("appid") == app_id:
                return key
        return None

    # Provided by _GamesMapMixin in production. The real versions only
    # normalise the wrapper key and pick the next free ordinal; the
    # fixture is already well-formed and never adds, so stubs suffice.
    @staticmethod
    def _ensure_shortcuts_root(shortcuts):
        if not isinstance(shortcuts, dict) or "shortcuts" not in shortcuts:
            return {"shortcuts": {}}
        return shortcuts

    @staticmethod
    def _allocate_new_shortcut_key(shortcuts_dict):
        return str(len(shortcuts_dict))


@pytest.fixture(autouse=True)
def _no_registry_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the registry off disk — this test is about shortcuts.vdf."""
    from unifideck.services.shortcut import registry

    monkeypatch.setattr(registry, "load_registry", dict)
    monkeypatch.setattr(registry, "save_registry", lambda _r: None)


BROKEN = "MANGOHUD=1 epic:123 %command%"
FIXED = "MANGOHUD=1 %command% epic:123"


@pytest.mark.asyncio
async def test_steady_state_sync_persists_the_reorder():
    """Nothing added/removed/reclaimed — the repair must still be written."""
    r = _Reconciler(BROKEN)
    counts = await r.reconcile([_Game()])

    entry = r._shortcuts["shortcuts"]["0"]
    assert entry["LaunchOptions"] == FIXED, "reorder was not applied"
    assert counts["added"] == 0
    assert counts["removed"] == 0
    assert counts["reclaimed"] == 0
    assert r.saved, (
        "shortcuts.vdf was never written: the repair exists only in memory "
        "and is lost when the process exits"
    )


@pytest.mark.asyncio
async def test_healthy_sync_does_not_write():
    """A steady-state sync with nothing to repair stays a no-op."""
    r = _Reconciler(FIXED)
    await r.reconcile([_Game()])

    assert r._shortcuts["shortcuts"]["0"]["LaunchOptions"] == FIXED
    assert not r.saved, "a no-op sync must not rewrite shortcuts.vdf"


@pytest.mark.asyncio
async def test_reordered_is_reported_in_counts():
    """The tally must surface repairs so they show up in the logs."""
    r = _Reconciler(BROKEN)
    counts = await r.reconcile([_Game()])
    assert counts.get("reordered") == 1
