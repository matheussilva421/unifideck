"""Pure Launch Options reordering — detect and fix Broken Ordering.

``reorder()`` returns the Canonical Form of a Launch Options string,
or ``None`` when the string is already healthy.  It reorders and
NEVER redacts: the multiset of tokens in the output equals the
input plus at most one ``%command%``.

Used by the reconcile loop (fork: auto-apply) and by the manual
"fix ordering" button (upstream: display as Suggestion).
"""

from __future__ import annotations

import re

from .launch_options import COMMAND_PLACEHOLDER, STORE_ID_PATTERN

_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _tokenize(raw: str) -> list[str]:
    """Split on whitespace outside quotes, preserving original text."""
    tokens: list[str] = []
    current = ""
    in_quotes = False
    quote_char = ""
    for char in raw:
        if char in ('"', "'") and not in_quotes:
            in_quotes = True
            quote_char = char
            current += char
        elif char == quote_char and in_quotes:
            in_quotes = False
            current += char
        elif char.isspace() and not in_quotes:
            if current:
                tokens.append(current)
                current = ""
        else:
            current += char
    if current:
        tokens.append(current)
    return tokens


def _find_store_idx(tokens: list[str]) -> int | None:
    """Index of the Store Token, or ``None`` when there isn't one.

    ``KEY=VALUE`` tokens are skipped: an env VALUE can itself contain
    a store-shaped substring (``FOO=gog:123``). Treating that as the
    Store Token would move the env var into token position, where it
    lands after the placeholder and Steam never exports it.
    """
    for i, tok in enumerate(tokens):
        if _ENV_RE.match(tok):
            continue
        if STORE_ID_PATTERN.search(tok):
            return i
    return None


def _has_env_after(tokens: list[str], cmd_idx: int) -> bool:
    """True if any ``KEY=VALUE`` token sits after the placeholder.

    Steam only exports assignments that precede ``%command%``, so one
    landing after it is silently dropped — Broken Ordering.
    """
    return any(
        _ENV_RE.match(tok) for tok in tokens[cmd_idx + 1:]
    )


def reorder(launch_options: str) -> str | None:
    """Return the reordered string, or ``None`` if already healthy."""
    if not launch_options or not launch_options.strip():
        return None

    tokens = _tokenize(launch_options)
    if not tokens:
        return None

    store_idx = _find_store_idx(tokens)
    if store_idx is None:
        return None

    cmd_indices = [i for i, t in enumerate(tokens) if t == COMMAND_PLACEHOLDER]

    # (c) more than one placeholder, or none at all.
    if len(cmd_indices) != 1:
        return _rebuild(tokens, store_idx, cmd_indices)

    cmd_idx = cmd_indices[0]

    # (a) env after the placeholder, or (b) token before it.
    if _has_env_after(tokens, cmd_idx) or store_idx < cmd_idx:
        return _rebuild(tokens, store_idx, cmd_indices)

    return None


def _rebuild(
    tokens: list[str],
    store_idx: int,
    cmd_indices: list[int],
) -> str:
    """Rebuild as ``<env> <wrappers> %command% <store token> <args>``.

    Non-env tokens are split on the placeholder (or, when there is
    none, on the Store Token): what came *before* is a wrapper and
    must stay before the placeholder, what came *after* is a game
    argument.  CheatDeck writes ``~/lsfg`` and ``~/fgmod/fgmod`` as
    prefix commands, so emitting them after the token would turn a
    wrapper into an argument to the launcher and silently disable it.
    """
    env: list[str] = []
    wrappers: list[str] = []
    args: list[str] = []
    store_token = tokens[store_idx]
    skip = {store_idx, *cmd_indices}
    boundary = cmd_indices[0] if cmd_indices else store_idx

    for i, tok in enumerate(tokens):
        if i in skip:
            continue
        if _ENV_RE.match(tok):
            env.append(tok)
        elif i < boundary:
            wrappers.append(tok)
        else:
            args.append(tok)

    parts = [*env, *wrappers, COMMAND_PLACEHOLDER, store_token, *args]
    return " ".join(parts)
