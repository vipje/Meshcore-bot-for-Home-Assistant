"""LongReplies: what happens to a reply that is too long for one radio message (card: Plugins -> LongReplies).

A channel message or DM longer than the radio's budget used to be split into several messages by the length guards in
command_manager.py (send_channel_message: patch_channel_message_length_guard.py; send_dm: upstream's own guard), at a
" | " separator where possible (patch_split_at_separator.py). That keeps the whole reply, but on a big, busy mesh a
part 2 costs airtime and often arrives late or not at all (GitHub issue #3).

With the card off (the default) nothing changes: the reply is split and every part is sent. With the card on:
1. parts listed in *Leave out first when too long* (for example "Received at") are dropped first, in that order,
   until the reply fits;
2. what is still too long is split, at most *Max parts per reply* parts (0 = all), the rest is dropped, and the last
   part ends with "..." (*Mark a shortened reply*);
3. *Split at " | "* off splits at a space, as upstream does.

Every reply that is too long gets one WARNING line in the log, card on or off, so the Problems page (Settings ->
Problems) counts per day and per command how often replies are split, shortened or cut. Only the command word, byte
counts and the labels of what was left out are logged, never the text of the reply.
"""
from __future__ import annotations

import contextvars
import re
from typing import Any, Callable, Optional

SECTION = "LongReplies"
DEFAULT_LEAVE_OUT = "Received at"
SEPARATOR = " | "
MARK = " …"

# The command word of the reply being sent (set by send_response, see patch_long_replies.py).
_label: contextvars.ContextVar[str] = contextvars.ContextVar("long_replies_label", default="")
_WORD = re.compile(r"^[a-z0-9_]{1,20}$")


def label_from_message(message: Any) -> str:
    """The first word of the incoming message (the command or keyword), or "" when it is not a plain word."""
    content = (getattr(message, "content", "") or "").strip().lower()
    word = content.split()[0] if content else ""
    word = word.lstrip("/!.#@")
    return word if _WORD.match(word) else ""


def set_label(label: str):
    return _label.set(label or "")


def reset_label(token) -> None:
    try:
        _label.reset(token)
    except (ValueError, LookupError):
        pass


def _bool(cfg: Any, key: str, default: bool) -> bool:
    try:
        return cfg.getboolean(SECTION, key, fallback=default)
    except (ValueError, AttributeError):
        return default


def settings(cfg: Any) -> dict:
    """The card's settings; card off (or no section) gives the old behaviour."""
    has = bool(cfg is not None and hasattr(cfg, "has_section") and cfg.has_section(SECTION))
    if not has:
        return {"enabled": False, "max_parts": 0, "leave_out": [], "split_at_separator": True, "mark": True,
                "channel": True, "dm": True}
    try:
        max_parts = max(0, int(str(cfg.get(SECTION, "max_parts", fallback="0")).strip() or 0))
    except ValueError:
        max_parts = 0
    raw = cfg.get(SECTION, "leave_out_first", fallback=DEFAULT_LEAVE_OUT)
    leave_out = [p.strip() for p in str(raw).split(",") if p.strip()]
    return {
        "enabled": _bool(cfg, "enabled", False),
        "max_parts": max_parts,
        "leave_out": leave_out,
        "split_at_separator": _bool(cfg, "split_at_separator", True),
        "mark": _bool(cfg, "mark_shortened", True),
        "channel": _bool(cfg, "channel_replies", True),
        "dm": _bool(cfg, "direct_messages", True),
    }


def _size(text: str) -> int:
    return len(text.encode("utf-8"))


def _leave_out(text: str, labels: list[str], max_bytes: int) -> tuple[str, list[str]]:
    """Drop " | "-parts that start with one of *labels* (never the first part), in order, until *text* fits."""
    dropped: list[str] = []
    for lab in labels:
        if _size(text) <= max_bytes:
            break
        parts = text.split(SEPARATOR)
        keep = [parts[0]] + [p for p in parts[1:] if not p.strip().lower().startswith(lab.lower())]
        if len(keep) < len(parts):
            text = SEPARATOR.join(keep)
            dropped.append(lab)
    return text, dropped


def _with_mark(text: str, max_bytes: int) -> str:
    """*text* plus " ...", shortened at a separator or space so it stays within *max_bytes*."""
    while text and _size(text + MARK) > max_bytes:
        cut = text.rfind(SEPARATOR)
        if cut <= 0:
            cut = text.rfind(" ")
        if cut <= 0:
            cut = len(text) - 1
        text = text[:cut].rstrip()
    return text + MARK


def shape(bot: Any, text: str, max_bytes: int, kind: str, split: Callable[..., list[str]],
          logger: Optional[Any] = None) -> list[str]:
    """The messages to send for *text* (too long for one message of *max_bytes*). *kind* is "channel" or "dm";
    *split* is CommandManager.split_text_into_utf8_chunks. Logs one WARNING line about what happened."""
    cfg = getattr(bot, "config", None)
    s = settings(cfg)
    active = s["enabled"] and s[kind]
    size_before = _size(text)
    actions: list[str] = []

    dropped: list[str] = []
    if active and s["leave_out"]:
        text, dropped = _leave_out(text, s["leave_out"], max_bytes)
        if dropped:
            actions.append("left out " + ", ".join(dropped))

    if _size(text) <= max_bytes:
        chunks = [text]
    else:
        prefer = s["split_at_separator"] if active else True
        try:
            chunks = split(text, max_bytes, prefer)
        except TypeError:          # an unpatched split function without the third argument
            chunks = split(text, max_bytes)
        total = len(chunks)
        if active and 0 < s["max_parts"] < total:
            chunks = chunks[:s["max_parts"]]
            if s["mark"]:
                chunks[-1] = _with_mark(chunks[-1], max_bytes)
            actions.append(f"sent {len(chunks)} of {total} parts, rest cut off")
        elif total > 1:
            actions.append(f"split into {total} parts")

    if logger is not None:
        label = _label.get() or "other"
        where = "a channel message" if kind == "channel" else "a DM"
        logger.warning("LongReplies: %s reply too long for %s (%d > %d bytes): %s", label, where, size_before,
                       max_bytes, "; ".join(actions) or "sent as is")
    return chunks
