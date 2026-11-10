#!/usr/bin/env python3
"""LongReplies: what happens to a reply that is too long for one radio message (card: Plugins -> LongReplies).

This service does nothing itself, it only carries the settings. modules/long_replies.py reads the section when a
channel message or DM is too long (patch_channel_message_length_guard.py, patch_long_replies.py). Off by default:
then every long reply is split and all parts are sent, as before. Every too-long reply is logged either way, so the
Problems page shows how often it happens before anyone changes a setting.
"""
from typing import Any

from .base_service import BaseServicePlugin


class LongRepliesService(BaseServicePlugin):
    config_section = "LongReplies"
    name = "longreplies"
    description = ("What to do with a reply that is too long for one message: leave parts out, send at most a few "
                   "parts. Off: split and send everything. Every long reply is counted on the Problems page.")

    settings_schema: list[dict[str, Any]] = [
        {"key": "max_parts", "label": "Max parts per reply", "type": "int", "default": 0, "min": 0, "max": 10,
         "help": "0 = send all parts. 1 = always one message: what does not fit is left out."},
        {"key": "leave_out_first", "label": "Leave out first when too long", "type": "str",
         "default": "Received at",
         "help": "Comma-separated. A ' | ' part of the reply that starts with one of these is left out first, in this "
                 "order, until the reply fits. The first part is always kept."},
        {"key": "split_at_separator", "label": "Split at \" | \"", "type": "bool", "default": True,
         "help": "Off: split at a space, as the bot does without this add-on."},
        {"key": "mark_shortened", "label": "Mark a shortened reply with …", "type": "bool", "default": True,
         "help": "When parts are cut off, the last message ends with …"},
        {"key": "channel_replies", "label": "Apply to channel replies", "type": "bool", "default": True},
        {"key": "direct_messages", "label": "Apply to direct messages", "type": "bool", "default": True},
    ]

    def __init__(self, bot: Any):
        super().__init__(bot)

    async def start(self) -> None:
        self.logger.info("LongReplies: on (settings from the LongReplies card apply to long replies)")
        self._running = True

    async def stop(self) -> None:
        self._running = False
