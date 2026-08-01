"""Tests for ``dispatcher._promote_env_tokens`` denylist behaviour.

Phase 2A: the allowlist (``UNIFIDECK_`` prefix only) is replaced by a
denylist of launcher-managed variables so that arbitrary user env vars
(e.g. ``MANGOHUD=1``) reach the game process via Proton.
"""
from __future__ import annotations

import pytest

from unifideck.launcher.dispatcher import _promote_env_tokens

DENYLIST = [
    "PROTONPATH",
    "WINEPREFIX",
    "STEAM_COMPAT_DATA_PATH",
    "STEAM_COMPAT_INSTALL_PATH",
    "GAMEID",
    "STORE",
    "PROTON_VERB",
    "DXVK_NVAPI_ALLOW_OTHER_DRIVERS",
    "ACTIVE_WINEPREFIX",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in [*DENYLIST, "MANGOHUD", "UNIFIDECK_TEST", "MY_VAR"]:
        monkeypatch.delenv(key, raising=False)


def test_arbitrary_env_var_is_promoted():
    import os
    _promote_env_tokens("MANGOHUD=1")
    assert os.environ.get("MANGOHUD") == "1"


def test_unifideck_prefixed_var_still_promoted():
    import os
    _promote_env_tokens("UNIFIDECK_TEST=hello")
    assert os.environ.get("UNIFIDECK_TEST") == "hello"


@pytest.mark.parametrize("key", DENYLIST)
def test_denylist_var_is_not_promoted(key):
    import os
    _promote_env_tokens(f"{key}=/evil")
    assert os.environ.get(key) is None


def test_existing_env_var_not_overwritten(monkeypatch):
    import os
    monkeypatch.setenv("MY_VAR", "original")
    _promote_env_tokens("MY_VAR=overwritten")
    assert os.environ["MY_VAR"] == "original"


def test_multiple_tokens_promoted():
    import os
    _promote_env_tokens("MANGOHUD=1 MY_VAR=2")
    assert os.environ.get("MANGOHUD") == "1"
    assert os.environ.get("MY_VAR") == "2"


def test_non_env_tokens_ignored():
    import os
    _promote_env_tokens("epic:123 %command%")
    assert "epic:123" not in os.environ
    assert "%command%" not in os.environ
