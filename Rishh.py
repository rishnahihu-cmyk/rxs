#!/usr/bin/env python3
# Multi-bot GC / Slide / Swipe tool (updated TOKENS & OWNER)
# - Spawns one Application per token and registers command handlers on each.
# - Commands available (same as original): /gcnc, /ncemo, /stopgcnc, /stopall, /delay, /status,
#   /targetslide, /stopslide, /slideSTYLE, /stopslideSTYLE, /swipe, /stopswipe,
#   /addsudo, /delsudo, /listsudo, /myid, /ping, /help
#
# NOTE: These tokens are sensitive. If they are real, revoke/rotate them after testing.

import asyncio
import functools
import json
import os
import random
import sys
import time
import logging
import platform
import socket

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
from datetime import datetime, timezone, timedelta
from typing import Dict

import httpx
from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import BadRequest, RetryAfter, TimedOut, NetworkError
from telegram.request import HTTPXRequest

IST_TZ = timezone(timedelta(hours=5, minutes=30))
BOT_START_TIME = time.time()   # set once at import, used by 'uptime

def ist_now() -> str:
    """Return current IST time as HH:MM:SS:ms"""
    now = datetime.now(IST_TZ)
    return now.strftime("%H:%M:%S:") + f"{now.microsecond // 1000:03d}"

# Detect HTTP/2 support once so header compression (HPACK) is used if 'h2' is installed
try:
    import h2  # noqa: F401
    _HTTP_VERSION = "2"
except ImportError:
    _HTTP_VERSION = "1.1"

def _build_request(pool_size: int = 32, read_timeout: float = 20.0) -> HTTPXRequest:
    """Build a persistent keep-alive HTTPXRequest to minimize TLS/header bandwidth."""
    return HTTPXRequest(
        connection_pool_size=pool_size,
        read_timeout=read_timeout,
        write_timeout=20.0,
        connect_timeout=20.0,
        pool_timeout=10.0,
        http_version=_HTTP_VERSION,
        httpx_kwargs={
            "limits": httpx.Limits(
                max_connections=pool_size,
                max_keepalive_connections=pool_size,
                keepalive_expiry=300.0,
            ),
        },
    )

# ---------------------------
# CONFIG
# ---------------------------
TOKENS = [
    "8684775337:AAHSdcpA3dK2Fo7NohbLSovqU9dY2GDPCA4",
    "8879825383:AAFMnx0hlpD2m2XubnRuWqPvoWofVyh-db4",
    "8743406831:AAGj4wgmtcsEpNGcGoho8adSGt7k_NZcUw4",
    "8832502170:AAHrHzFyhemOcO0XW39NYPxRG98qmJQaILk",
    "8899390842:AAGV1OYFlkNfCRzhjouV-ByJUPA0aWYTmI8",
    "8930180055:AAF_rNeiddVmR1hMGaer-3KrIpIgUMgNSOE",
    "8997929841:AAG11qbUdM0jmHLzrXAgsk5FFrTcRnOqAxw",
    "8985666576:AAFHDd2hppRmp-dmgar_c4nZiDi2eMXGDqU",
    "8884699375:AAE13_kdzVvbi5EsF0n4EUrass9e01CZnJM",
    "8843006227:AAGnesAJ9EwsyziAk9aKD-cTVOD4BHSkbEE",
]

# Owner / initial sudo (you provided "Chat id 6552187447)
OWNER_ID = 6002928421
SUDO_FILE = "sudo.json"

# ---------------------------
# WMO TEXTS & EMOJIS
# ---------------------------
WMO_TEXTS = [
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(💮)࿐ྂ",
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(🏵️)࿐ྂ",
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(🪻)࿐ྂ",
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(🌻)࿐ྂ",
"˚˖𓍢ִ໋⋆⋆.˚(🌼)࿐ྂ",
"˚˖𓍢ִ໋⋆𐙚⋆.˚(🌸)࿐ྂ",
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(🪷)࿐ྂ",
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(🌷)࿐ྂ",
"˚˖𓍢ִ໋⋆⋆.˚(🌺)࿐ྂ",
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(🌹)࿐ྂ",
"˚˖𓍢ִ໋⋆𐙚⋆.˚(💐)࿐ྂ",
"˚˖𓍢ִ໋⋆⋆.˚(🌼)࿐ྂ",
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(🌻)࿐ྂ",
"˚˖𓍢ִ໋⋆⋆.˚(🪻)࿐ྂ",
"˚˖𓍢ִ໋⋆  𐙚⋆.˚(🏵️)࿐ྂ",
"˚˖𓍢ִ໋⋆𐙚⋆.˚(🌸)࿐ྂ",
"˚˖𓍢ִ໋⋆ 𐙚⋆.˚(🪷)࿐ྂ",
]

NCEMO_EMOJIS = [
    "❤️","🧡","💛","💚","💙","💜","🤎","🖤","🤍","🩷","🩵","🩶","♥️",
    "❤️","🧡","💛","💚","💙","💜","🤎","🖤","🤍","🩷","🩵","🩶","♥️",
    "❤️","🧡","💛","💚","💙","💜","🤎","🖤","🤍","🩷","🩵","🩶","♥️",
    "❤️","🧡","💛","💚","💙","💜","🤎","🖤","🤍","🩷","🩵","🩶","♥️",
    "❤️","🧡","💛","💚","💙","💜","🤎","🖤","🤍","🩷","🩵","🩶"
]

EMOSTYLE_PATTERNS = [
    "साम दाम दंड भेद【{target}】की गांर में बड़ा छेद\n\n\n\n                                              ⋆.˚"
    "{emo}༘⋆\n\n\nसाम दाम दंड भेद【{target}】की गांर में बड़ा छेद\n\n\n\n                                              ⋆.˚{emo}༘⋆\n\n\nसाम दाम दंड भेद【{target}】की गांर में बड़ा छेद\n\n\n\n                                              ⋆.˚{emo}༘⋆\n\n\nसाम दाम दंड भेद【{target}】की गांर में बड़ा छेद\n\n\n\n                                              ⋆.˚{emo}༘⋆\n\n\nसाम दाम दंड भेद【{target}】की गांर में बड़ा छेद\n\n\n\n                                              ⋆.˚{emo}༘⋆\n\n\nसाम दाम दंड भेद【{target}】की गांर में बड़ा छेद\n\n\n\n                                              ⋆.˚{emo}༘⋆\n\n\nसाम दाम दंड भेद【{target}】की गांर में बड़ा छेद\n\n\n\n                                              ⋆.˚{emo}༘⋆",
]

STYLE_PATTERNS = [
    "[ text ] 🖤",
    "[ text ] 🩷",
    "[ text ] 🤍",
    "[ text ] ❤️"
]

IMPACT_EMOJIS = [
    # Reaction faces
    "😀","😁","😂","🤣","😃","😄","😅","😆","😉","😊","😋","😎","😍","🥰","🤩",
    "😏","😒","😞","😔","😟","😕","🙁","☹️","😣","😖","😫","😩","🥺","😢","😭",
    "😤","😠","😡","🤬","🤯","😳","🥵","🥶","😱","😨","😰","😥","😓","🤗","🤔",
    "🤭","🤫","🤥","😶","😐","😑","😬","🙄","😯","😦","😧","😮","😲","🥱","😴",
    "🤤","😪","😵","🤐","🥴","🤢","🤮","🤧","😷","🤒","🤕","🤑","🤠","😈","👿",
    "👹","👺","💀","☠️","👻","👽","🤖","🎃","😺","😸","😹","😻","😼","😽","🙀",
    # Flags
    "🏳️","🏴","🚩","🏁","🏳️‍🌈","🏳️‍⚧️",
    "🇦🇫","🇦🇱","🇩🇿","🇦🇩","🇦🇴","🇦🇷","🇦🇲","🇦🇺","🇦🇹","🇦🇿",
    "🇧🇩","🇧🇪","🇧🇷","🇧🇳","🇧🇬","🇨🇦","🇨🇳","🇨🇴","🇭🇷","🇨🇿",
    "🇩🇰","🇪🇬","🇪🇹","🇫🇮","🇫🇷","🇩🇪","🇬🇭","🇬🇷","🇭🇺","🇮🇳",
    "🇮🇩","🇮🇷","🇮🇶","🇮🇪","🇮🇱","🇮🇹","🇯🇵","🇯🇴","🇰🇿","🇰🇪",
    "🇰🇷","🇰🇼","🇱🇧","🇲🇾","🇲🇽","🇲🇦","🇳🇵","🇳🇱","🇳🇿","🇳🇬",
    "🇳🇴","🇴🇲","🇵🇰","🇵🇸","🇵🇭","🇵🇱","🇵🇹","🇶🇦","🇷🇴","🇷🇺",
    "🇸🇦","🇷🇸","🇸🇬","🇿🇦","🇪🇸","🇱🇰","🇸🇩","🇸🇪","🇨🇭","🇸🇾",
    "🇹🇼","🇹🇿","🇹🇭","🇹🇳","🇹🇷","🇺🇦","🇦🇪","🇬🇧","🇺🇸","🇻🇳","🇾🇪",
]

emoSTYLE_tasks: Dict[int, asyncio.Task] = {}
impact_tasks: Dict[int, asyncio.Task] = {}


# ---------------------------
# GLOBAL STATE
# ---------------------------
if os.path.exists(SUDO_FILE):
    try:
        with open(SUDO_FILE, "r", encoding="utf-8") as f:
            _loaded = json.load(f)
            SUDO_USERS = set(int(x) for x in _loaded)
    except Exception:
        SUDO_USERS = {OWNER_ID}
else:
    SUDO_USERS = {OWNER_ID}
with open(SUDO_FILE, "w", encoding="utf-8") as f:
    json.dump(list(SUDO_USERS), f)

def save_sudo():
    with open(SUDO_FILE, "w", encoding="utf-8") as f:
        json.dump(list(SUDO_USERS), f)

group_tasks: Dict[int, Dict[str, asyncio.Task]] = {}
STYLE_tasks: Dict[int, asyncio.Task] = {}
react_emojis: Dict[int, list] = {}   # chat_id -> [emoji, ...]
slide_targets = set()
slideSTYLE_targets = set()
swipe_mode = {}
apps, bots = [], []
delay = 0.1

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s:%(name)s:%(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# ---------------------------
# DECORATORS
# ---------------------------
def only_sudo(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        uid = update.effective_user.id
        if uid not in SUDO_USERS and uid != OWNER_ID:
            return await update.message.reply_text("❌𝐒ᴏʀʀʏ 🇧 🇧 🇾  𝐀ᴘ 𝐆ᴀʀʀᴇʙ 𝐇ᴏ.")
        return await func(update, context)
    return wrapper

def only_owner(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        uid = update.effective_user.id
        if uid != OWNER_ID:
            return await update.message.reply_text("❌ RISH KO ABBU BOL.")
        return await func(update, context)
    return wrapper

# ---------------------------
# BOT LOOP used by gcnc/ncemo  (all bots parallel)
# ---------------------------
async def bot_loop(bot, chat_id, base, mode):
    i = 0
    while True:
        try:
            if mode == "WMO":
                text = f"{base} {WMO_TEXTS[i % len(WMO_TEXTS)]}"
            else:
                text = f"{base} {NCEMO_EMOJIS[i % len(NCEMO_EMOJIS)]}"
            await bot.set_chat_title(chat_id, text)
            i += 1
            await asyncio.sleep(delay)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] Bot error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

async def STYLE_loop(bot, chat_id, text):
    while True:
        try:
            STYLE_pattern = random.choice(STYLE_PATTERNS)
            STYLE_text = STYLE_pattern.replace("[ text ]", text).replace("[ Text ]", text).replace("[ any text ]", text)
            await bot.send_message(chat_id=chat_id, text=STYLE_text)
            await asyncio.sleep(delay)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] STYLE error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

# ---------------------------
# COMMANDS
# ---------------------------
MENU_PHOTO = "11e899b80bc85bd39d07953159e62ff9.jpg"

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤍 Bot is active. Use !help to see commands.")

@only_sudo
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu = (
        "╭━━━ ✦ 𝗕𝗢𝗧 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦 ✦ ━━━╮\n\n"
        "🌿 𝗧𝗜𝗧𝗟𝗘 𝗟𝗢𝗢𝗣𝗦\n"
        "  !gcnc <text>       ·  !stopgcnc\n"
        "  !ncemo <text>      ·  !stopncemo\n"
        "  !impact <text>     ·  !stopimpact\n"
        "  !long <text>       ·  !stoplong\n"
        "  !ist <text>        ·  !stopist\n"
        "  !rxsnc <target>    ·  !stoprxsnc\n"
        "  !rxsnc2 <target>   ·  !stoprxsnc2\n"
        "  !rxsnc3 <target>   ·  !stoprxsnc3\n"
        "  !rxsnc4 <target>   ·  !stoprxsnc4\n\n"
        "🎨 𝗦𝗧𝗬𝗟𝗘 & 𝗦𝗪𝗜𝗣𝗘\n"
        "  !STYLEloop <text>  ·  !stopSTYLE\n"
        "  !emoSTYLE <text>   ·  !stopemoSTYLE\n"
        "  !swipe <name>      ·  !stopswipe\n\n"
        "💬 𝗥𝗘𝗣𝗟𝗬 𝗧𝗢 𝗔 𝗠𝗘𝗦𝗦𝗔𝗚𝗘\n"
        "  !targetslide      ·  !stopslide\n"
        "  !slideSTYLE       ·  !stopslideSTYLE\n\n"
        "⚙️ 𝗧𝗢𝗢𝗟𝗦\n"
        "  !flood <text>      ·  !stopflood\n"
        "  !stopall           ·  !delay <sec>\n"
        "  !status            ·  !ping  ·  !myid\n"
        "  !help  ·  !menu\n"
        "  !addsudo  ·  !delsudo  ·  !listsudo\n\n"
        "╰━━ Use the ! prefix for text commands ━━╯"
    )
    if os.path.exists(MENU_PHOTO):
        with open(MENU_PHOTO, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=menu)
    else:
        await update.message.reply_text(menu)

@only_sudo
async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    end_time = time.time()
    latency = int((end_time - start_time) * 1000)
    await msg.edit_text(f"🏓 Pong! ✅ {latency} ms")

@only_sudo
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your ID: {update.effective_user.id}")

# --- GC Loops ---
@only_sudo
async def gcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /gcnc <text>")
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"gcnc_{id(bot)}"
        if key not in group_tasks[chat_id]:
            group_tasks[chat_id][key] = asyncio.create_task(bot_loop(bot, chat_id, base, "WMO"))
    await update.message.reply_text("🔄चुदाई suru hua.")

@only_sudo
async def ncemo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /ncemo <text>")
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"ncemo_{id(bot)}"
        if key not in group_tasks[chat_id]:
            group_tasks[chat_id][key] = asyncio.create_task(bot_loop(bot, chat_id, base, "emoji"))
    await update.message.reply_text("🔄 Emoji loop started.")

@only_sudo
async def stopgcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        keys = [k for k in list(group_tasks[chat_id]) if k.startswith("gcnc_")]
        for k in keys:
            group_tasks[chat_id][k].cancel()
            del group_tasks[chat_id][k]
        if keys:
            return await update.message.reply_text("⏹ GCNC loop stopped in this GC.")
    await update.message.reply_text("⏹ No active GCNC loop in this GC.")

@only_sudo
async def stopncemo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        keys = [k for k in list(group_tasks[chat_id]) if k.startswith("ncemo_")]
        for k in keys:
            group_tasks[chat_id][k].cancel()
            del group_tasks[chat_id][k]
        if keys:
            return await update.message.reply_text("⏹ Emoji loop stopped in this GC.")
    await update.message.reply_text("⏹ No active emoji loop in this GC.")

@only_sudo
async def stopall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    # Explicitly remove rxsnc tasks, then stop all remaining group tasks.
    if chat_id in group_tasks:
        rxsnc_keys = [
            key for key in list(group_tasks[chat_id])
            if key.startswith("rxsnc_")
        ]
        for key in rxsnc_keys:
            group_tasks[chat_id][key].cancel()
            del group_tasks[chat_id][key]
        for task in group_tasks[chat_id].values():
            task.cancel()
        group_tasks[chat_id] = {}
    # Stop long_tasks
    if chat_id in long_tasks:
        long_tasks[chat_id].cancel()
        del long_tasks[chat_id]
    # Stop STYLE_tasks
    if chat_id in STYLE_tasks:
        STYLE_tasks[chat_id].cancel()
        del STYLE_tasks[chat_id]
    # Stop emoSTYLE_tasks
    if chat_id in emoSTYLE_tasks:
        emoSTYLE_tasks[chat_id].cancel()
        del emoSTYLE_tasks[chat_id]
    # Stop impact_tasks
    if chat_id in impact_tasks:
        impact_tasks[chat_id].cancel()
        del impact_tasks[chat_id]
    # Stop swipe mode
    swipe_mode.pop(chat_id, None)
    # Stop react mode
    react_emojis.pop(chat_id, None)
    await update.message.reply_text("⏹ All loops in this group stopped.")

@only_sudo
async def delay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global delay
    if not context.args:
        return await update.message.reply_text(f"⏱ Current delay: {delay}s")
    try:
        delay = float(context.args[0])
        await update.message.reply_text(f"✅ Delay set to {delay}s")
    except:
        await update.message.reply_text("⚠️ Invalid number.")

@only_sudo
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📊 Active Loops:\n"
    for chat_id, tasks in group_tasks.items():
        msg += f"Chat {chat_id}: {len(tasks)} bots running\n"
    if not group_tasks:
        msg += "No active loops."
    await update.message.reply_text(msg)

# --- SUDO ---
@only_owner
async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        uid = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("⚠️ Invalid User ID.")
    if uid:
        SUDO_USERS.add(uid)
        save_sudo()
        await update.message.reply_text(f"✅ {uid} added as sudo.")
    else:
        await update.message.reply_text("⚠️ Reply to a user or provide ID: !addsudo <id>")

@only_owner
async def delsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        uid = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("⚠️ Invalid User ID.")
    if uid:
        if uid in SUDO_USERS:
            SUDO_USERS.remove(uid)
            save_sudo()
            await update.message.reply_text(f"🗑 {uid} removed from sudo.")
        else:
            await update.message.reply_text("⚠️ User not in sudo list.")
    else:
        await update.message.reply_text("⚠️ Reply to a user or provide ID: !delsudo <id>")

@only_sudo
async def listsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 SUDO USERS:\n" + "\n".join(map(str, SUDO_USERS)))

# --- Slide / STYLE / Swipe ---
@only_sudo
async def targetslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        slide_targets.add(update.message.reply_to_message.from_user.id)
        await update.message.reply_text("🎯 Target slide added.")
    else:
        await update.message.reply_text("⚠️ Reply to a user to target them.")

@only_sudo
async def stopslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        slide_targets.discard(uid)
        await update.message.reply_text("🛑 Target slide stopped.")
    else:
        await update.message.reply_text("⚠️ Reply to a user to stop targeting them.")

@only_sudo
async def slideSTYLE(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        slideSTYLE_targets.add(update.message.reply_to_message.from_user.id)
        await update.message.reply_text("🎯 SlideSTYLE target added.")
    else:
        await update.message.reply_text("⚠️ Reply to a user to target them.")

@only_sudo
async def stopslideSTYLE(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        slideSTYLE_targets.discard(uid)
        await update.message.reply_text("🛑 SlideSTYLE stopped.")
    else:
        await update.message.reply_text("⚠️ Reply to a user to stop targeting them.")

@only_sudo
async def swipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /swipe <name>")
    name = " ".join(context.args)
    chat_id = update.message.chat_id
    swipe_mode[chat_id] = name
    await update.message.reply_text(f"✨ Swipe mode enabled for: {name}")

@only_sudo
async def stopswipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in swipe_mode:
        del swipe_mode[chat_id]
        await update.message.reply_text("🛑 Swipe mode disabled.")
    else:
        await update.message.reply_text("⚠️ Swipe mode not active in this chat.")

@only_sudo
async def STYLEloop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /STYLEloop <text>")
    text = " ".join(context.args)
    chat_id = update.message.chat_id
    bot = context.bot
    if chat_id in STYLE_tasks:
        STYLE_tasks[chat_id].cancel()
    task = asyncio.create_task(STYLE_loop(bot, chat_id, text))
    STYLE_tasks[chat_id] = task
    await update.message.reply_text("🔄 STYLE loop started.")

@only_sudo
async def stopSTYLE(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in STYLE_tasks:
        STYLE_tasks[chat_id].cancel()
        del STYLE_tasks[chat_id]
        await update.message.reply_text("🛑 STYLE loop stopped.")
    else:
        await update.message.reply_text("⚠️ No STYLE loop active in this chat.")

async def emoSTYLE_loop(bot, chat_id, text):
    i = 0
    while True:
        try:
            pattern = random.choice(EMOSTYLE_PATTERNS)
            emo = NCEMO_EMOJIS[i % len(NCEMO_EMOJIS)]
            STYLE_text = pattern.replace("{target}", text).replace("{emo}", emo)
            await bot.send_message(chat_id=chat_id, text=STYLE_text)
            i += 1
            await asyncio.sleep(delay)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] EmoSTYLE error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

@only_sudo
async def emoSTYLE(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /emoSTYLE <text>")
    text = " ".join(context.args)
    chat_id = update.message.chat_id
    bot = context.bot
    if chat_id in emoSTYLE_tasks:
        emoSTYLE_tasks[chat_id].cancel()
    task = asyncio.create_task(emoSTYLE_loop(bot, chat_id, text))
    emoSTYLE_tasks[chat_id] = task
    await update.message.reply_text("🔄 Emoji STYLE started.")

@only_sudo
async def stopemoSTYLE(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in emoSTYLE_tasks:
        emoSTYLE_tasks[chat_id].cancel()
        del emoSTYLE_tasks[chat_id]
        await update.message.reply_text("🛑 Emoji STYLE stopped.")
    else:
        await update.message.reply_text("⚠️ No emoji STYLE active in this chat.")

async def impact_loop(bot, chat_id, target):
    i = 0
    while True:
        try:
            emo = IMPACT_EMOJIS[i % len(IMPACT_EMOJIS)]
            text = f"{emo}_/-> {target}"
            await bot.set_chat_title(chat_id, text)
            i += 1
            await asyncio.sleep(delay)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] Impact error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

LONG_SUFFIX = "𝙆𝙐𝙏𝙄𝙔𝘼 𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙𒈙"

long_tasks: Dict[int, asyncio.Task] = {}

async def long_loop(bot, chat_id, target):
    i = 0
    while True:
        try:
            emo = NCEMO_EMOJIS[i % len(NCEMO_EMOJIS)]
            text = f"{emo} {target} {LONG_SUFFIX}"
            await bot.set_chat_title(chat_id, text)
            i += 1
            await asyncio.sleep(delay)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] Long error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

RXSNC_WALL_EMOJIS = ("🪽", "🐦‍🔥", "🦖", "🪷", "🍭", "🌂", "🪼", "🐚", "🧃", "🍧")
RXSNC_EMOJI_INDEX = {}

def next_rxsnc_emoji(chat_id):
    """Give each update in a chat the next distinct emoji variant."""
    index = RXSNC_EMOJI_INDEX.get(chat_id, 0)
    RXSNC_EMOJI_INDEX[chat_id] = (index + 1) % len(RXSNC_WALL_EMOJIS)
    return RXSNC_WALL_EMOJIS[index]

def build_wall_text(emoji, target):
    # Add the fixed prefix to the supplied target and fill a 300-character wall.
    target_length = 300
    heading = f"{target} ƦƝƊ"
    wall_char = "𒐫"
    row = f"{wall_char * 8} {emoji}"
    line_break = "\n"
    if len(heading) + len(row) > target_length:
        raise ValueError("Target is too long to fit the rxsnc wall.")

    parts = [heading + row]
    while len(line_break.join(parts)) + len(line_break) + len(row) <= target_length:
        parts.append(row)

    text = line_break.join(parts)
    remaining = target_length - len(text)
    if remaining:
        # Use visible glyphs to fill the title to its full length.
        text = text[:-len(emoji)] + wall_char * remaining + emoji
    return text

async def rxsnc_loop(bot, chat_id, target):
    wall_texts = [build_wall_text(e, target) for e in RXSNC_WALL_EMOJIS]
    n = len(wall_texts)
    i = 0
    while True:
        try:
            await bot.set_chat_title(chat_id, wall_texts[i % n])
            i += 1
            await asyncio.sleep(0.5)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] rxsnc error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

@only_sudo
async def rxsnc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: !rxsnc <text>")
    target = " ".join(context.args)
    try:
        build_wall_text(RXSNC_WALL_EMOJIS[0], target)
    except ValueError as e:
        return await update.message.reply_text(f"⚠️ {e}")
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"rxsnc_{id(bot)}"
        if key not in group_tasks[chat_id]:
            group_tasks[chat_id][key] = asyncio.create_task(rxsnc_loop(bot, chat_id, target))
    await update.message.reply_text("🔄 rxsnc wall loop started.")

@only_sudo
async def stoprxsnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    tasks = group_tasks.get(chat_id, {})
    keys = [key for key in list(tasks) if key.startswith("rxsnc_")]
    for key in keys:
        tasks[key].cancel()
        del tasks[key]
    try:
        if keys:
            return await update.message.reply_text("⏹ rxsnc loop stopped.")
        await update.message.reply_text("⏹ No active rxsnc loop in this chat.")
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
        if keys:
            await update.message.reply_text("⏹ rxsnc loop stopped.")
        else:
            await update.message.reply_text("⏹ No active rxsnc loop in this chat.")

RXSNC2_TARGET_LENGTH = 320
RXSNC2_WALL_CHAR = "╌"
RXSNC2_WALL_EMOJIS = ("🌙", "✨", "🪐", "💫", "🌌", "🔮", "🦋", "💎")
RXSNC2_UPDATE_INTERVAL = 0.45

def build_rxsnc2_text(target, variation):
    """Build a symmetrical, exactly 320-Python-character title."""
    emoji = RXSNC2_WALL_EMOJIS[variation % len(RXSNC2_WALL_EMOJIS)]
    partner = RXSNC2_WALL_EMOJIS[(variation + len(RXSNC2_WALL_EMOJIS) // 2) % len(RXSNC2_WALL_EMOJIS)]
    center = RXSNC2_WALL_EMOJIS[(variation + 2) % len(RXSNC2_WALL_EMOJIS)]

    heading = f"{target} ƦƝƊ"
    top = f"╭─ ✦ {emoji} · {partner} ✦ ─╮"
    bottom = f"╰─ ✦ {partner} · {emoji} ✦ ─╯"
    center_row = f"│ {center} │"
    fixed_text = f"{heading}\n{top}\n{center_row}\n{bottom}"
    filler_count = RXSNC2_TARGET_LENGTH - len(fixed_text)
    if filler_count < 0:
        raise ValueError("Target is too long to fit the rxsnc2 320-character title.")

    left_count = filler_count // 2
    right_count = filler_count - left_count
    padded_center_row = (
        f"│{RXSNC2_WALL_CHAR * left_count} {center} "
        f"{RXSNC2_WALL_CHAR * right_count}│"
    )
    text = f"{heading}\n{top}\n{padded_center_row}\n{bottom}"
    if len(text) != RXSNC2_TARGET_LENGTH:
        raise RuntimeError("rxsnc2 title generation did not produce exactly 320 characters.")
    return text

async def rxsnc2_loop(bot, chat_id, target):
    wall_texts = [build_rxsnc2_text(target, i) for i in range(len(RXSNC2_WALL_EMOJIS))]
    i = 0
    while True:
        try:
            await bot.set_chat_title(chat_id, wall_texts[i % len(wall_texts)])
            i += 1
            await asyncio.sleep(RXSNC2_UPDATE_INTERVAL)
        except RetryAfter as e:
            await asyncio.sleep(max(float(e.retry_after), 1))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] rxsnc2 error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

@only_sudo
async def rxsnc2_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: !rxsnc2 <text>")
    target = " ".join(context.args)
    try:
        build_rxsnc2_text(target, 0)
    except ValueError as e:
        return await update.message.reply_text(f"⚠️ {e}")
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"rxsnc2_{id(bot)}"
        task = group_tasks[chat_id].get(key)
        if task is None or task.done():
            group_tasks[chat_id][key] = asyncio.create_task(rxsnc2_loop(bot, chat_id, target))
    await update.message.reply_text("🔄 rxsnc2 wall loop started.")

@only_sudo
async def stoprxsnc2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    tasks = group_tasks.get(chat_id, {})
    keys = [key for key in list(tasks) if key.startswith("rxsnc2_")]
    for key in keys:
        tasks[key].cancel()
        del tasks[key]
    if keys:
        await update.message.reply_text("⏹ rxsnc2 loop stopped.")
    else:
        await update.message.reply_text("⏹ No active rxsnc2 loop in this chat.")

RXSNC3_TARGET_LENGTH = 128
RXSNC3_WALL_CHAR = "╌"
RXSNC3_WALL_EMOJIS = ("🧿", "🎆", "🌟", "🪄", "🪸", "🥀", "☄️", "🪁")

def build_rxsnc3_text(target, variation):
    """Build a framed, multi-row title within Telegram's chat-title limit."""
    emoji = RXSNC3_WALL_EMOJIS[variation % len(RXSNC3_WALL_EMOJIS)]
    partner = RXSNC3_WALL_EMOJIS[(variation + 3) % len(RXSNC3_WALL_EMOJIS)]
    accent = RXSNC3_WALL_EMOJIS[(variation + 5) % len(RXSNC3_WALL_EMOJIS)]
    heading = f"{target} ƦƝƊ"
    top = f"╔════〔 {emoji} · {partner} 〕════╗"
    upper_row = f"║  ◈ {accent}  ◇  {partner} ◈  ║"
    lower_row = f"║  ✧ {emoji}  ⋈  {accent} ✧  ║"
    bottom = f"╚════〔 {partner} · {emoji} 〕════╝"
    fixed_text = "\n".join((heading, top, upper_row, lower_row, bottom))
    filler_count = RXSNC3_TARGET_LENGTH - len(fixed_text)
    if filler_count < 0:
        raise ValueError("Target is too long to fit the rxsnc3 128-character title.")

    def widen_row(row, amount):
        left_count = amount // 2
        right_count = amount - left_count
        return row.replace("║", f"║{RXSNC3_WALL_CHAR * left_count}", 1)[:-1] + (
            f"{RXSNC3_WALL_CHAR * right_count}║"
        )

    upper_extra = filler_count // 2
    lower_extra = filler_count - upper_extra
    text = "\n".join((
        heading,
        top,
        widen_row(upper_row, upper_extra),
        widen_row(lower_row, lower_extra),
        bottom,
    ))
    if len(text) != RXSNC3_TARGET_LENGTH:
        raise RuntimeError("rxsnc3 title generation did not produce exactly 128 characters.")
    return text

async def rxsnc3_loop(bot, chat_id, target):
    wall_texts = [build_rxsnc3_text(target, i) for i in range(len(RXSNC3_WALL_EMOJIS))]
    i = 0
    while True:
        try:
            await bot.set_chat_title(chat_id, wall_texts[i % len(wall_texts)])
            i += 1
            await asyncio.sleep(delay)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] rxsnc3 error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

@only_sudo
async def rxsnc3_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: !rxsnc3 <text>")
    target = " ".join(context.args)
    try:
        build_rxsnc3_text(target, 0)
    except ValueError as e:
        return await update.message.reply_text(f"⚠️ {e}")
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"rxsnc3_{id(bot)}"
        task = group_tasks[chat_id].get(key)
        if task is None or task.done():
            group_tasks[chat_id][key] = asyncio.create_task(rxsnc3_loop(bot, chat_id, target))
    await update.message.reply_text("🔄 rxsnc3 framed wall loop started.")

@only_sudo
async def stoprxsnc3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    tasks = group_tasks.get(chat_id, {})
    keys = [key for key in list(tasks) if key.startswith("rxsnc3_")]
    for key in keys:
        tasks[key].cancel()
        del tasks[key]
    if keys:
        await update.message.reply_text("⏹ rxsnc3 loop stopped.")
    else:
        await update.message.reply_text("⏹ No active rxsnc3 loop in this chat.")

RXSNC4_TARGET_LENGTH = 300
RXSNC4_WALL_CHAR = "╍"
RXSNC4_WALL_EMOJIS = ("🛡️", "🦁", "⚜️", "🗝️", "🏰", "🦚", "🔱", "🌠")
RXSNC4_UPDATE_INTERVAL = 0.5

def build_rxsnc4_text(target, variation):
    """Build a 300-character heraldic frame with target and branding first."""
    emoji = RXSNC4_WALL_EMOJIS[variation % len(RXSNC4_WALL_EMOJIS)]
    partner = RXSNC4_WALL_EMOJIS[(variation + 3) % len(RXSNC4_WALL_EMOJIS)]
    accent = RXSNC4_WALL_EMOJIS[(variation + 5) % len(RXSNC4_WALL_EMOJIS)]
    heading = f"{target} ƦƝƊ"
    top = f"╔═════〔 {emoji} ⚜ {partner} 〕═════╗"
    upper_row = f"║  ◈ {accent} · {partner} · {emoji} ◈  ║"
    lower_row = f"║  ✧ {partner} ⋈ {accent} ⋈ {emoji} ✧  ║"
    bottom = f"╚═════〔 {partner} ⚜ {emoji} 〕═════╝"
    fixed_text = "\n".join((heading, top, upper_row, lower_row, bottom))
    filler_count = RXSNC4_TARGET_LENGTH - len(fixed_text)
    if filler_count < 0:
        raise ValueError("Target is too long to fit the rxsnc4 300-character title.")

    def widen_row(row, amount):
        left_count = amount // 2
        right_count = amount - left_count
        return (
            row[0]
            + RXSNC4_WALL_CHAR * left_count
            + row[1:-1]
            + RXSNC4_WALL_CHAR * right_count
            + row[-1]
        )

    upper_extra = filler_count // 2
    lower_extra = filler_count - upper_extra
    text = "\n".join((
        heading,
        top,
        widen_row(upper_row, upper_extra),
        widen_row(lower_row, lower_extra),
        bottom,
    ))
    if len(text) != RXSNC4_TARGET_LENGTH:
        raise RuntimeError("rxsnc4 title generation did not produce exactly 300 characters.")
    return text

async def rxsnc4_loop(bot, chat_id, target):
    wall_texts = [build_rxsnc4_text(target, i) for i in range(len(RXSNC4_WALL_EMOJIS))]
    i = 0
    while True:
        try:
            await bot.set_chat_title(chat_id, wall_texts[i % len(wall_texts)])
            i += 1
            await asyncio.sleep(RXSNC4_UPDATE_INTERVAL)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] rxsnc4 error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

@only_sudo
async def rxsnc4_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: !rxsnc4 <text>")
    target = " ".join(context.args)
    try:
        build_rxsnc4_text(target, 0)
    except ValueError as e:
        return await update.message.reply_text(f"⚠️ {e}")
    if not bots:
        return await update.message.reply_text("⚠️ No initialized bot is available for rxsnc4.")
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"rxsnc4_{id(bot)}"
        task = group_tasks[chat_id].get(key)
        if task is None or task.done():
            group_tasks[chat_id][key] = asyncio.create_task(rxsnc4_loop(bot, chat_id, target))
    await update.message.reply_text("🔄 rxsnc4 heraldic title loop started.")

@only_sudo
async def stoprxsnc4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    tasks = group_tasks.get(chat_id, {})
    keys = [key for key in list(tasks) if key.startswith("rxsnc4_")]
    for key in keys:
        tasks[key].cancel()
        del tasks[key]
    if keys:
        await update.message.reply_text("⏹ rxsnc4 loop stopped.")
    else:
        await update.message.reply_text("⏹ No active rxsnc4 loop in this chat.")

@only_sudo
async def long_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /long <text>")
    target = " ".join(context.args)
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"long_{id(bot)}"
        if key not in group_tasks[chat_id]:
            group_tasks[chat_id][key] = asyncio.create_task(long_loop(bot, chat_id, target))
    await update.message.reply_text("💠 Long loop started.")

@only_sudo
async def stoplong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        keys = [k for k in list(group_tasks[chat_id]) if k.startswith("long_")]
        for k in keys:
            group_tasks[chat_id][k].cancel()
            del group_tasks[chat_id][k]
        if keys:
            return await update.message.reply_text("🛑 Long loop stopped.")
    await update.message.reply_text("⚠️ No long loop active in this chat.")

@only_sudo
async def impact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /impact <text>")
    target = " ".join(context.args)
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"impact_{id(bot)}"
        if key not in group_tasks[chat_id]:
            group_tasks[chat_id][key] = asyncio.create_task(impact_loop(bot, chat_id, target))
    await update.message.reply_text("💥 Impact loop started.")

@only_sudo
async def stopimpact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        keys = [k for k in list(group_tasks[chat_id]) if k.startswith("impact_")]
        for k in keys:
            group_tasks[chat_id][k].cancel()
            del group_tasks[chat_id][k]
        if keys:
            return await update.message.reply_text("🛑 Impact loop stopped.")
    await update.message.reply_text("⚠️ No impact loop active in this chat.")

# ---------------------------
# FLOOD LOOP
# ---------------------------
FLOOD_LINE = "ᴷᴴᴬ ᴷᴱ ᴮᵁᴿᴳᴱᴿ {target} Oʀ ᴜsᴋᴇ 𝗧ᴀᴛ𝗧ᴇ  ᴷᴵ ᴹᴬᴬ ᶜᴴᴼᴰᵁᴺᴳᴬ ᴳᴴᴬᴿ ᴳᴴᴬᴿ________<{emo}>{ist}"
FLOOD_REPEATS = 11
FLOOD_BLANK_LINES = 6   # blank lines between each repetition

async def flood_loop(bot, chat_id, target):
    i = 0
    while True:
        try:
            emo = IMPACT_EMOJIS[i % len(IMPACT_EMOJIS)]
            ist = ist_now()
            single = FLOOD_LINE.format(target=target, emo=emo, ist=ist)
            separator = "\n" * (FLOOD_BLANK_LINES + 1)
            message = separator.join([single] * FLOOD_REPEATS)
            await bot.send_message(chat_id, message)
            i += 1
            await asyncio.sleep(delay)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] Flood error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

@only_sudo
async def flood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /flood <target>")
    target = " ".join(context.args)
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"flood_{id(bot)}"
        if key not in group_tasks[chat_id]:
            group_tasks[chat_id][key] = asyncio.create_task(flood_loop(bot, chat_id, target))
    await update.message.reply_text("💀 Flood started.")

@only_sudo
async def stopflood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        keys = [k for k in list(group_tasks[chat_id]) if k.startswith("flood_")]
        for k in keys:
            group_tasks[chat_id][k].cancel()
            del group_tasks[chat_id][k]
        if keys:
            return await update.message.reply_text("🛑 Flood stopped.")
    await update.message.reply_text("⚠️ No flood active in this chat.")

# ---------------------------
# IST NAME-CHANGER LOOP
# ---------------------------
async def ist_loop(bot, chat_id, target):
    while True:
        try:
            text = f"{target} {ist_now()}"
            await bot.set_chat_title(chat_id, text)
            await asyncio.sleep(delay)
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except (TimedOut, NetworkError):
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[WARN] IST loop error in chat {chat_id}: {e}")
            await asyncio.sleep(1)

@only_sudo
async def ist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /ist <target>")
    target = " ".join(context.args)
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = f"ist_{id(bot)}"
        if key not in group_tasks[chat_id]:
            group_tasks[chat_id][key] = asyncio.create_task(ist_loop(bot, chat_id, target))
    await update.message.reply_text("🕐 IST name loop started.")

@only_sudo
async def stopist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        keys = [k for k in list(group_tasks[chat_id]) if k.startswith("ist_")]
        for k in keys:
            group_tasks[chat_id][k].cancel()
            del group_tasks[chat_id][k]
        if keys:
            return await update.message.reply_text("🛑 IST loop stopped.")
    await update.message.reply_text("⚠️ No IST loop active in this chat.")

@only_sudo
async def uptime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secs = int(time.time() - BOT_START_TIME)
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m, s   = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    uptime_str = " ".join(parts)
    started_at = datetime.fromtimestamp(BOT_START_TIME, tz=IST_TZ).strftime("%d %b %Y  %H:%M:%S IST")
    await update.message.reply_text(
        f"⏱️ 𝗨𝗽𝘁𝗶𝗺𝗲\n\n"
        f"🤍 Running for  {uptime_str}\n"
        f"🎀 Started at  {started_at}\n"
        f"💅🏻 Bots loaded  {len(bots)}"
    )

# ---------------------------
# REACT MODE
# ---------------------------
async def react_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user:
        return
    chat_id = msg.chat_id
    if chat_id not in react_emojis or not react_emojis[chat_id]:
        return
    if msg.from_user.id not in SUDO_USERS:
        return
    reactions = [ReactionTypeEmoji(emoji=e) for e in react_emojis[chat_id]]
    await asyncio.gather(
        *(
            bot.set_message_reaction(
                chat_id=chat_id,
                message_id=msg.message_id,
                reaction=reactions,
            )
            for bot in bots
        ),
        return_exceptions=True,
    )

@only_sudo
async def react_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: !react <emoji> <emoji> ...")
    chat_id = update.message.chat_id
    react_emojis[chat_id] = list(context.args)
    await update.message.reply_text(f"💬 React mode on  {'  '.join(context.args)}")

@only_sudo
async def stopreact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    react_emojis.pop(chat_id, None)
    await update.message.reply_text("🛑 React mode off.")

# ---------------------------
# PREFIX DISPATCHER  (trigger: ! instead of /)
# ---------------------------
CMD_PREFIX = "!"

COMMAND_MAP = {
    "start":          start_cmd,
    "help":           help_cmd,
    "ping":           ping_cmd,
    "myid":           myid,
    "gcnc":           gcnc,
    "ncemo":          ncemo,
    "stopgcnc":       stopgcnc,
    "stopncemo":      stopncemo,
    "stopall":        stopall,
    "delay":          delay_cmd,
    "status":         status_cmd,
    "addsudo":        addsudo,
    "delsudo":        delsudo,
    "listsudo":       listsudo,
    "targetslide":    targetslide,
    "stopslide":      stopslide,
    "styleslide":     slideSTYLE,
    "stopslidestyle": stopslideSTYLE,
    "slideSTYLE":     slideSTYLE,
    "stopslideSTYLE": stopslideSTYLE,
    "swipe":          swipe,
    "stopswipe":      stopswipe,
    "STYLEloop":      STYLEloop_cmd,
    "styleloop":      STYLEloop_cmd,
    "stopSTYLE":      stopSTYLE,
    "stopstyle":      stopSTYLE,
    "emoSTYLE":       emoSTYLE,
    "emostyle":       emoSTYLE,
    "stopemoSTYLE":   stopemoSTYLE,
    "stopemostyle":   stopemoSTYLE,
    "impact":         impact,
    "stopimpact":     stopimpact,
    "long":           long_cmd,
    "stoplong":       stoplong,
    "rxsnc":          rxsnc_cmd,
    "stoprxsnc":      stoprxsnc,
    "rxsnc2":         rxsnc2_cmd,
    "stoprxsnc2":     stoprxsnc2,
    "rxsnc3":         rxsnc3_cmd,
    "stoprxsnc3":     stoprxsnc3,
    "rxsnc4":         rxsnc4_cmd,
    "stoprxsnc4":     stoprxsnc4,
    "flood":          flood_cmd,
    "stopflood":      stopflood,
    "ist":            ist_cmd,
    "stopist":        stopist,
    "uptime":         uptime_cmd,
    "react":          react_cmd,
    "stopreact":      stopreact_cmd,
    "menu":           help_cmd,
}

# Track which updates have already been processed so only 1 bot replies
_processed_updates = set()
_MAX_PROCESSED = 5000  # keep memory bounded

async def prefix_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text
    if text.startswith(CMD_PREFIX):
        parts = text[len(CMD_PREFIX):].split()
    elif text.startswith("/"):
        parts = text[1:].split()
    else:
        return
    if not parts:
        return
    # Strip @botname if present (e.g. /help@MyBot -> help)
    cmd = parts[0].split("@")[0]
    handler_func = COMMAND_MAP.get(cmd) or COMMAND_MAP.get(cmd.lower())
    if not handler_func:
        return

    # Only let one bot respond to avoid duplicate replies across multiple bots
    uid = (msg.chat_id, msg.message_id)
    if uid in _processed_updates:
        return
    _processed_updates.add(uid)
    # Prune old entries to avoid memory leak
    if len(_processed_updates) > _MAX_PROCESSED:
        excess = len(_processed_updates) - (_MAX_PROCESSED // 2)
        for _ in range(excess):
            _processed_updates.pop()

    context.args = parts[1:]
    await handler_func(update, context)

# ---------------------------
# HTTP HEALTH CHECK SERVER
# ---------------------------
async def handle_http_request(reader, writer):
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not request_line:
            return

        req = request_line.decode('utf-8').strip()
        parts = req.split(' ')
        
        # Parse method and path safely
        method = parts[0] if len(parts) >= 1 else ""
        path = parts[1] if len(parts) >= 2 else "/"

        if method == 'HEAD':
            if path == '/health':
                status = "200 OK"
                content_length = 2  # Length of "OK"
            elif path == '/':
                status = "200 OK"
                content_length = 14 # Length of "Bot is running"
            else:
                status = "404 Not Found"
                content_length = 9  # Length of "Not Found"
        else:
            # Reject GET and all other methods
            status = "405 Method Not Allowed"
            content_length = 0
            
        # Build the HTTP response headers. 
        # For a HEAD request (or 405 response), we don't append a body payload.
        response = (
            f"HTTP/1.1 {status}\r\n"
            f"Content-Type: text/plain\r\n"
            f"Content-Length: {content_length}\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

# ---------------------------
# MAIN
# ---------------------------
def print_banner(n_bots: int):
    now = datetime.now(IST_TZ).strftime("%d %b %Y  %H:%M:%S IST")
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"
    print(flush=True)
    print("  🎀  ʀɪsʜ ʙᴏᴛ", flush=True)
    print(flush=True)
    print(f"  🤍  ʜᴏsᴛ      {hostname}", flush=True)
    print(f"  🤍  ᴘʟᴀᴛꜰᴏʀᴍ  {platform.system()} {platform.release()}", flush=True)
    print(f"  🤍  ᴘʏᴛʜᴏɴ    {platform.python_version()}", flush=True)
    print(f"  🤍  ʙᴏᴛs      {n_bots}", flush=True)
    print(f"  🤍  sᴛᴀʀᴛᴇᴅ   {now}", flush=True)
    print(flush=True)

async def main():
    global apps, bots
    
    for token_index, token in enumerate(TOKENS, start=1):
        try:
            app = (
                Application.builder()
                .token(token)
                .concurrent_updates(True)
                .request(_build_request(pool_size=32, read_timeout=20.0))
                .get_updates_request(_build_request(pool_size=4, read_timeout=60.0))
                .build()
            )
            app.add_handler(MessageHandler(filters.TEXT, prefix_handler), group=0)
            app.add_handler(MessageHandler(filters.ALL, react_handler), group=1)
            apps.append(app)
            bots.append(app.bot)
            print(f"  ✅  Bot #{token_index} configured", flush=True)
        except Exception as e:
            safe_error = str(e).replace(token, "[redacted]")
            print(
                f"  ❌  Bot #{token_index} configuration failed: "
                f"{type(e).__name__}: {safe_error}",
                flush=True,
            )
    
    if not apps:
        print("[FATAL] No bots loaded. Exiting.", flush=True)
        return

    async def initialize_bot(app, bot_number):
        backoff = 2
        for attempt in range(1, 4):
            try:
                await app.initialize()
                return app
            except (TimedOut, NetworkError) as e:
                if attempt < 3:
                    print(
                        f"  ⚠️  Bot #{bot_number} initialization timed out/network error; "
                        f"retrying in {backoff}s ({attempt}/3): {e}",
                        flush=True,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    print(
                        f"  ❌  Bot #{bot_number} initialization failed after 3 attempts: "
                        f"{type(e).__name__}: {e}",
                        flush=True,
                    )
            except Exception as e:
                safe_error = str(e).replace(app.bot.token, "[redacted]")
                print(
                    f"  ❌  Bot #{bot_number} initialization failed; skipping: "
                    f"{type(e).__name__}: {safe_error}",
                    flush=True,
                )
                try:
                    await app.shutdown()
                except Exception:
                    pass
                return None
        return None

    init_results = await asyncio.gather(
        *(initialize_bot(app, i) for i, app in enumerate(apps, start=1))
    )
    initialized_apps = [app for app in init_results if app is not None]

    apps[:] = initialized_apps
    bots[:] = [app.bot for app in apps]
    if not apps:
        print("[FATAL] No bot tokens initialized successfully. Exiting.", flush=True)
        return

    print_banner(len(apps))

    print(flush=True)
    print("  🤍  ʙᴏᴛ ʟɪsᴛ", flush=True)
    for i, app in enumerate(apps, 1):
        uname = app.bot.username or "unknown"
        print(f"      {i:>2}. @{uname}", flush=True)
    print(flush=True)

    started_apps = []
    poller_started = False
    for app in apps:
        try:
            await app.start()
            if not poller_started:
                await app.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=["message"],
                    timeout=50,
                )
                poller_started = True
            started_apps.append(app)
        except Exception as e:
            print(f"  ❌  Bot startup failed; skipping this bot: {type(e).__name__}: {e}", flush=True)
            try:
                if app.updater and app.updater.running:
                    await app.updater.stop()
                if app.running:
                    await app.stop()
                await app.shutdown()
            except Exception:
                pass

    apps[:] = started_apps
    bots[:] = [app.bot for app in apps]
    if not apps:
        print("[FATAL] No bots started successfully. Exiting.", flush=True)
        return
    
    print("  🟢  All bots polling — prefix: !\n", flush=True)
    
    # Start the HTTP Server concurrently on the same AsyncIO event loop
    port = int(os.environ.get("PORT", "10000"))
    http_server = await asyncio.start_server(handle_http_request, '0.0.0.0', port)
    print(f"  🟢  HTTP Server listening on 0.0.0.0:{port} for HEAD checks\n", flush=True)
    
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        print("[INFO] Shutting down...")
        if 'http_server' in locals():
            http_server.close()
            await http_server.wait_closed()
        for app in apps:
            try:
                if app.updater and app.updater.running:
                    await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except Exception as e:
                print(f"[WARN] Shutdown error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
