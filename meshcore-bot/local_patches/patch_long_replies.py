#!/usr/bin/env python3
"""Source patch: the LongReplies card (modules/long_replies.py) for direct messages, and the command word in its log line.

Runs once during the Docker build (see patch_webviewer.py for the shared mechanics).

- send_dm: upstream's "Central DM length guard" split a DM longer than 158 bytes into parts and logged
  "DM to <name> exceeds ...". It now asks modules/long_replies.py what to send (leave parts out, at most N parts,
  card off = split and send everything, as before) and that module logs one line without the recipient's name.
- send_response: remembers the command word of the message being answered (for example "test"), so the LongReplies
  log line can say which command's reply was too long. Reset when the reply has been sent.

The channel side is in patch_channel_message_length_guard.py, splitting at " | " in patch_split_at_separator.py.
"""
import pathlib
import sys

ROOT = pathlib.Path.cwd()


def patch(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        sys.exit(
            f"PATCH FAILED - anchor text found {count} time(s) in {path} "
            f"(expected 1; upstream code likely changed):\n{old!r}"
        )
    p.write_text(text.replace(old, new))
    print(f"Patched {path}")


FILE = "modules/command_manager.py"

patch(
    FILE,
    """                chunks = self.split_text_into_utf8_chunks(content, dm_max_bytes)
                self.logger.warning(
                    "DM to %s exceeds %d UTF-8 bytes (%d); auto-splitting into %d chunk(s)",
                    sanitize_name(contact_name),
                    dm_max_bytes,
                    content_bytes,
                    len(chunks),
                )
""",
    """                # LongReplies card (modules/long_replies.py): optionally leave parts out or limit the
                # number of parts, and log one line about every too-long DM (card on or off).
                from .long_replies import shape as _long_replies_shape
                chunks = _long_replies_shape(self.bot, content, dm_max_bytes, "dm",
                                             self.split_text_into_utf8_chunks, self.logger)
""",
)

patch(
    FILE,
    """        try:
            # Render-only invocation (see render_command_output): collect the text and""",
    """        _long_replies_token = None
        try:
            # Render-only invocation (see render_command_output): collect the text and""",
)

patch(
    FILE,
    """            rate_limit_key = self.get_rate_limit_key(message)
            if message.is_dm:
                return await self.send_dm(
                    message.sender_pubkey or message.sender_id or "",""",
    """            rate_limit_key = self.get_rate_limit_key(message)
            # The command word, for the LongReplies log line (modules/long_replies.py).
            from .long_replies import label_from_message as _lr_label, set_label as _lr_set
            _long_replies_token = _lr_set(_lr_label(message))
            if message.is_dm:
                return await self.send_dm(
                    message.sender_pubkey or message.sender_id or "",""",
)

patch(
    FILE,
    """        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")
            return False
""",
    """        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")
            return False
        finally:
            if _long_replies_token is not None:
                from .long_replies import reset_label as _lr_reset
                _lr_reset(_long_replies_token)
""",
)
