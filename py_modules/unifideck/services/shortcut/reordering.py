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
        elif char == " " and not in_quotes:
            if current:
                tokens.append(current)
                current = ""
        else:
            current += char
    if current:
        tokens.append(current)
    return tokens


def reorder(launch_options: str) -> str | None:
    """Return the reordered string, or ``None`` if already healthy."""
    if not launch_options or not launch_options.strip():
        return None

    tokens = _tokenize(launch_options)
    if not tokens:
        return None

    store_idx: int | None = None
    for i, tok in enumerate(tokens):
        if STORE_ID_PATTERN.search(tok):
            store_idx = i
            break

    if store_idx is None:
        return None

    cmd_indices = [i for i, t in enumerate(tokens) if t == COMMAND_PLACEHOLDER]

    if not cmd_indices:
        return _rebuild(tokens, store_idx, [])
    if len(cmd_indices) > 1:
        return _rebuild(tokens, store_idx, cmd_indices)

    cmd_idx = cmd_indices[0]

    for i, tok in enumerate(tokens):
        if i > cmd_idx and _ENV_RE.match(tok):
            return _rebuild(tokens, store_idx, cmd_indices)

    if store_idx < cmd_idx:
        return _rebuild(tokens, store_idx, cmd_indices)

    return None


def _rebuild(
    tokens: list[str],
    store_idx: int,
    cmd_indices: list[int],
) -> str:
    env: list[str] = []
    rest: list[str] = []
    store_token = tokens[store_idx]
    skip = {store_idx, *cmd_indices}

    for i, tok in enumerate(tokens):
        if i in skip:
            continue
        if _ENV_RE.match(tok):
            env.append(tok)
        else:
            rest.append(tok)

    parts = [*env, COMMAND_PLACEHOLDER, store_token, *rest]
    return " ".join(parts)
