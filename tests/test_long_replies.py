"""LongReplies card (modules/long_replies.py + patch_long_replies.py, patch_channel_message_length_guard.py,
patch_split_at_separator.py): too-long replies are split (card off) or shortened (card on), and always logged.

Runs in the simulated build tree: usage test_long_replies.py <tree>.
"""
import asyncio
import configparser
import logging
import os
import sys
import types

TREE = sys.argv[1] if len(sys.argv) > 1 else os.environ["SIM_TREE"]
os.chdir(TREE)
sys.path.insert(0, TREE)

from modules import long_replies as LR  # noqa: E402
from modules import problem_log as P  # noqa: E402
from modules.command_manager import CommandManager  # noqa: E402

fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append((record.levelname, record.getMessage()))


def bot(section=None):
    cfg = configparser.ConfigParser()
    cfg["Bot"] = {"bot_name": "X"}
    if section is not None:
        cfg["LongReplies"] = section
    return types.SimpleNamespace(config=cfg)


def size(text):
    return len(text.encode("utf-8"))


log = logging.getLogger("long_replies_test")
log.propagate = False
cap = Capture()
log.addHandler(cap)
split = CommandManager.split_text_into_utf8_chunks

TEST = ("ack @[Jan] | a1b2,c3d4,e5f6,0a1b,2c3d,4e5f,6a7b,8c9d,0e1f,1a2b,3c4d,5e6f (12 hops) | 2B/hop | "
        "SNR: 6.5 dB | RSSI: -92 dBm | 1.2 km | Received at: 22:13:34")
MAX = 120
check(size(TEST) > 150 and size(TEST) - len(" | Received at: 22:13:34") <= 150,
      f"test reply: too long for 150, fits without 'Received at' ({size(TEST)} bytes)")

# ------------------------------------------------------------ split function
check(split(TEST, MAX) == split(TEST, MAX, True), "split: prefer_separator defaults to on")
on = split(TEST, MAX, True)
off = split(TEST, MAX, False)
check(all(size(c) <= MAX for c in on + off), "split: every part fits, both ways")
check(not on[1].startswith("|") and TEST.startswith(on[0] + " | "),
      f"split at ' | ': the first message ends at a part boundary ({on[0]!r})")
check(len(off[0]) > len(on[0]), f"split at a space: the first message is fuller ({off[0]!r})")

# ------------------------------------------------------------ card off: as before
LR.set_label("test")
cap.lines.clear()
chunks = LR.shape(bot(), TEST, MAX, "channel", split, log)
check(chunks == on, "card off (no section): split, all parts sent, as before")
check(bool(cap.lines) and cap.lines[-1][0] == "WARNING", "card off: still one WARNING line")
check("LongReplies: test reply too long for a channel message" in cap.lines[-1][1]
      and "split into 2 parts" in cap.lines[-1][1], f"card off: the line says what happened ({cap.lines[-1][1]!r})")
chunks = LR.shape(bot({"enabled": "false", "max_parts": "1"}), TEST, MAX, "channel", split, log)
check(chunks == on, "card switched off: its settings do not apply")

# ------------------------------------------------------------ card on
CARD = {"enabled": "true", "max_parts": "1", "leave_out_first": "Received at", "split_at_separator": "true",
        "mark_shortened": "true", "channel_replies": "true", "direct_messages": "true"}
cap.lines.clear()
chunks = LR.shape(bot(CARD), TEST, 150, "channel", split, log)
check(len(chunks) == 1 and "Received at" not in chunks[0] and chunks[0].endswith("1.2 km"),
      f"leave out first: 'Received at' dropped, the rest fits in one message ({chunks})")
check("left out Received at" in cap.lines[-1][1] and "cut off" not in cap.lines[-1][1], "log: left out, nothing cut")

cap.lines.clear()
chunks = LR.shape(bot(CARD), TEST, MAX, "channel", split, log)
check(len(chunks) == 1 and size(chunks[0]) <= MAX and chunks[0].endswith(" …"),
      f"max 1 part: one message within the limit, ending with ... ({chunks})")
check("Received at" not in chunks[0], "max 1 part: the listed part was left out first")
check("left out Received at; sent 1 of 2 parts, rest cut off" in cap.lines[-1][1], f"log: {cap.lines[-1][1]!r}")

chunks = LR.shape(bot(dict(CARD, mark_shortened="false")), TEST, MAX, "channel", split, log)
check(len(chunks) == 1 and not chunks[0].endswith("…"), "mark off: no ...")

chunks = LR.shape(bot(dict(CARD, max_parts="0", leave_out_first="")), TEST, MAX, "channel", split, log)
check(chunks == on, "max parts 0 and nothing to leave out: all parts, as with the card off")

chunks = LR.shape(bot(dict(CARD, max_parts="0", leave_out_first="", split_at_separator="false")), TEST, MAX,
                  "channel", split, log)
check(chunks == off, "split at ' | ' off: splits at a space")

chunks = LR.shape(bot(dict(CARD, channel_replies="false")), TEST, MAX, "channel", split, log)
check(chunks == on, "channel replies off: the card does not apply to a channel message")
chunks = LR.shape(bot(dict(CARD, channel_replies="false")), TEST, MAX, "dm", split, log)
check(len(chunks) == 1, "... but still to a DM")
chunks = LR.shape(bot(dict(CARD, direct_messages="false")), TEST, MAX, "dm", split, log)
check(chunks == on, "direct messages off: the card does not apply to a DM")

chunks = LR.shape(bot(dict(CARD, max_parts="5", leave_out_first="ack")), TEST, MAX, "channel", split, log)
check(chunks[0].startswith("ack @[Jan]"), "the first part is never left out")

check(LR.settings(bot({"enabled": "true"}).config)["leave_out"] == ["Received at"],
      "default for Leave out first: Received at")
check(LR.settings(bot({"enabled": "true", "max_parts": "x"}).config)["max_parts"] == 0, "bad number: 0")

# ------------------------------------------------------------ Problems page groups the lines per command
a = "LongReplies: test reply too long for a channel message (182 > 148 bytes): split into 2 parts"
b = "LongReplies: test reply too long for a channel message (171 > 140 bytes): split into 3 parts"
c = "LongReplies: path reply too long for a channel message (171 > 140 bytes): split into 3 parts"
check(P.kind_of(a) == P.kind_of(b) != P.kind_of(c), "Problems page: one kind per command and action")

# ------------------------------------------------------------ label from send_response, reset afterwards
LR.set_label("")
seen = []


class FakeManager:
    logger = log

    def get_rate_limit_key(self, message):
        return None

    async def send_channel_message(self, channel, content, command_id=None, **kw):
        seen.append(LR._label.get())
        return True

    async def send_dm(self, recipient, content, command_id=None, **kw):
        seen.append(LR._label.get())
        return True


msg = types.SimpleNamespace(content="/Test hello", is_dm=False, channel="#test", capture_sink=None,
                            reply_scope=None, sender_id="Jan", sender_pubkey=None)
asyncio.run(CommandManager.send_response(FakeManager(), msg, "hi"))
check(seen == ["test"], f"send_response: label = command word ({seen})")
check(LR._label.get() == "", "send_response: label reset afterwards")
msg.content = "Jan de Vries zegt hoi"
check(LR.label_from_message(msg) == "jan", "label: only the first word")
msg.content = "☃☃"
check(LR.label_from_message(msg) == "", "label: no odd characters")

# ------------------------------------------------------------ patched source
src = open(os.path.join(TREE, "modules/command_manager.py"), encoding="utf-8").read()
check(src.count("_long_replies_shape(") == 2, "both length guards use LongReplies (channel and DM)")
check("auto-splitting into" not in src, "old split log lines replaced (no recipient name in the log)")

print(f"\n{len(fails)} failures")
sys.exit(1 if fails else 0)
