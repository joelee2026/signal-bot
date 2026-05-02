"""
Dual Signal Matcher Bot
========================
Monitors @NinaGoldCircle and @Goldhunterworldfx
Sends YOU a message ONLY when BOTH post the same direction (BUY/SELL)
Each alert shows the timestamp of BOTH signals so you can judge freshness.

SETUP:
  pip install telethon python-telegram-bot
  Fill in CONFIG below, then: python signal_matcher_bot.py
"""

import asyncio
import re
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telegram import Bot

# ─────────────────────────────────────────
#  CONFIG — fill these in
# ─────────────────────────────────────────
API_ID       = 32675268               # from https://my.telegram.org
API_HASH     = "9476f11f0ce645fe2fc90ee4e3032dff"      # from https://my.telegram.org
BOT_TOKEN    = "8729447892:AAEYNqfMoaM_dZ-R0LyuXKQG-2fQJWG_iO4"     # from @BotFather
YOUR_CHAT_ID = 1077381439            # your chat ID — get from @userinfobot

CHANNEL_1 = "@NinaGoldCircle"
CHANNEL_2 = "@Goldhunterworldfx"

# Max minutes between the two signals to still count as a match
MATCH_WINDOW_MINUTES = 60

# Your local timezone offset from UTC (Malaysia = +8)
TIMEZONE_OFFSET_HOURS = 8
# ─────────────────────────────────────────


def to_local(dt: datetime) -> str:
    """Convert UTC datetime to local time string."""
    local = dt + timedelta(hours=TIMEZONE_OFFSET_HOURS)
    return local.strftime("%Y-%m-%d  %H:%M:%S") + f"  (UTC+{TIMEZONE_OFFSET_HOURS})"


def extract_direction(text: str):
    text_upper = text.upper()
    if re.search(r'\bBUY\b', text_upper):
        return "BUY"
    if re.search(r'\bSELL\b', text_upper):
        return "SELL"
    return None


def extract_sl(text: str) -> str:
    m = re.search(r'SL[\s\-:]*([0-9.]+)', text, re.IGNORECASE)
    return m.group(1) if m else "N/A"


def extract_tps(text: str) -> list:
    return re.findall(r'TP\d*[\s\-:]*([0-9.]+)', text, re.IGNORECASE)


def extract_entry(text: str) -> str:
    m = re.search(r'(?:buy|sell)\s+at\s+([0-9.]+)', text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'(?:buy|sell)\s+([0-9.]+(?:-[0-9.]+)?)', text, re.IGNORECASE)
    if m:
        return m.group(1)
    return "N/A"


# ── In-memory store ───────────────────────────────────────────────────────────
recent = {
    CHANNEL_1: [],
    CHANNEL_2: [],
}

def purge_old(channel: str):
    cutoff = datetime.utcnow() - timedelta(minutes=MATCH_WINDOW_MINUTES)
    recent[channel] = [s for s in recent[channel] if s["time"] > cutoff]

def find_match(direction: str, other_channel: str):
    for entry in recent[other_channel]:
        if entry["direction"] == direction:
            return entry
    return None


# ── Telegram clients ──────────────────────────────────────────────────────────
from telethon.sessions import StringSession
SESSION = "1BVtsOL8BuxUxnVMSaHDNyi7TL2VcKqq93sp2vrc6zabtrMVIkTneRJboalmfpuze-OTw00MGuS3oph1U1MdBbuS8raQhUReItEknXO3DSFQ0Rkq0RlGyJwGEhNaG650a-2wo9OuNSUOYdEyYXucOtnMZkoq8DN432vJjhEwd51w3qfPlD8y_PbIyYAAZaazznV91o-prDu8t7nIbeeWfs8msJTEw-4Ge1rj8scvDHIBd942sf4js8nF2I5FP1uSMNyKvax-x2UmO-QOg3itflFWQjFdkABmYrUJQH5hN8sEZwxa-9xtECYr4vDbs8-RYS0Gdq8csmLwoN6Fj65bvEEWZcLsK_uU="
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
notify_bot = Bot(token=BOT_TOKEN)


@client.on(events.NewMessage(chats=[CHANNEL_1, CHANNEL_2]))
async def on_message(event):
    text      = event.message.text or ""
    direction = extract_direction(text)
    now       = datetime.utcnow()

    if not direction:
        return

    chat     = await event.get_chat()
    username = f"@{chat.username}" if chat.username else str(chat.id)

    if username not in (CHANNEL_1, CHANNEL_2):
        return

    other = CHANNEL_2 if username == CHANNEL_1 else CHANNEL_1

    purge_old(username)
    purge_old(other)

    match = find_match(direction, other)

    if match:
        time_new  = now
        time_old  = match["time"]
        gap_total = int((time_new - time_old).total_seconds())
        gap_mins  = gap_total // 60
        gap_secs  = gap_total % 60
        gap_str   = f"{gap_mins}m {gap_secs}s" if gap_mins > 0 else f"{gap_secs}s"

        # Freshness indicator based on gap
        if gap_mins < 5:
            freshness = "🟢 Very fresh — both signals close together"
        elif gap_mins < 15:
            freshness = "🟡 Fresh — within 15 min"
        elif gap_mins < 30:
            freshness = "🟠 Getting old — 15-30 min apart"
        else:
            freshness = "🔴 Old signal — over 30 min apart, be careful"

        tps_new = extract_tps(text)
        tps_old = match["tps"]

        msg = (
            f"⚡ *GOLD DUAL SIGNAL CONFIRMED!* ⚡\n"
            f"{'─' * 32}\n"
            f"📈 Direction : *{direction}*\n"
            f"{'─' * 32}\n"
            f"*{other}*  ← first signal\n"
            f"   🕐 `{to_local(time_old)}`\n"
            f"   📍 Entry : `{match['entry']}`\n"
            f"   🛑 SL    : `{match['sl']}`\n"
            f"   🎯 TPs   : `{', '.join(tps_old) if tps_old else 'N/A'}`\n\n"
            f"*{username}*  ← second signal\n"
            f"   🕐 `{to_local(time_new)}`\n"
            f"   📍 Entry : `{extract_entry(text)}`\n"
            f"   🛑 SL    : `{extract_sl(text)}`\n"
            f"   🎯 TPs   : `{', '.join(tps_new) if tps_new else 'N/A'}`\n"
            f"{'─' * 32}\n"
            f"⏱ Gap between signals : *{gap_str}*\n"
            f"{freshness}"
        )

        await notify_bot.send_message(
            chat_id=YOUR_CHAT_ID,
            text=msg,
            parse_mode="Markdown"
        )
        print(f"[SENT] {direction} | gap={gap_str} | {other} + {username}")

        # Clear matched entry to avoid duplicate alerts
        recent[other] = [s for s in recent[other] if s["direction"] != direction]

    else:
        recent[username].append({
            "direction": direction,
            "entry":     extract_entry(text),
            "sl":        extract_sl(text),
            "tps":       extract_tps(text),
            "text":      text,
            "time":      now,
        })
        print(f"[WAITING] {username} | {direction} at {to_local(now)} — waiting for {other}...")


async def main():
    print("Gold Signal Matcher Bot started")
    print(f"   Watching : {CHANNEL_1}  +  {CHANNEL_2}")
    print(f"   Notify   : chat ID {YOUR_CHAT_ID}")
    print(f"   Window   : {MATCH_WINDOW_MINUTES} min")
    print(f"   Timezone : UTC+{TIMEZONE_OFFSET_HOURS}\n")
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
