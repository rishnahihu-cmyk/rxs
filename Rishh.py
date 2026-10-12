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

IST_TZ = timezone(timedelta(hours=5, minutes=30))
BOT_START_TIME = time.time()   # set once at import, used by 'uptime

def ist_now() -> str:
    """Return current IST time as HH:MM:SS:ms"""
    now = datetime.now(IST_TZ)
    return now.strftime("%H:%M:%S:") + f"{now.microsecond // 1000:03d}"
from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import RetryAfter, TimedOut, NetworkError

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
    caption = (
        "💅🏻RɪSʜ Bᴏᴛ Aᴄᴛɪᴠᴇ\n"
        "                  \n"
        "                       WᴇʟCᴏᴍᴇ BʙʏBᴏʏ🤍\n\n"
        "Tʏᴘᴇ 'ʜᴇʟᴘ ᴛᴏ Sᴇᴇ Aʟʟ Cᴍᴅs 🎀"
    )
    if os.path.exists(MENU_PHOTO):
        with open(MENU_PHOTO, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=caption)
    else:
        await update.message.reply_text(caption)

@only_sudo
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu = (
        "🎀💅🏻🤍💅🏻🎀💅🏻🤍💅🏻🎀\n\n"
        "🌸 𝗡𝗮𝗺𝗲 𝗟𝗼𝗼𝗽𝘀\n"
        "  🤍 'gcnc <text>\n"
        "  🤍 'ncemo <text>\n"
        "  🤍 'impact <text>\n"
        "  🤍 'long <text>\n"
        "  🤍 'ist <text>\n"
        "  🌸 'stopgcnc  •  'stopimpact\n"
        "  🌸 'stoplong  •  'stopist\n\n"
        "💀 𝗙𝗹𝗼𝗼𝗱\n"
        "  🤍 'flood <text>\n"
        "  🌸 'stopflood\n\n"
        "✨ 𝗦𝘁𝘆𝗹𝗲 𝗟𝗼𝗼𝗽𝘀\n"
        "  🤍 'STYLEloop <text>\n"
        "  🤍 'emoSTYLE <text>\n"
        "  🤍 'swipe <name>\n"
        "  🌸 'stopSTYLE  •  'stopemoSTYLE\n"
        "  🌸 'stopswipe\n\n"
        "💬 𝗦𝗹𝗶𝗱𝗲𝘀 (𝗿𝗲𝗽𝗹𝘆)\n"
        "  🤍 'targetslide  •  'stopslide\n"
        "  🤍 'slideSTYLE  •  'stopslideSTYLE\n\n"
        "🛑 𝗚𝗹𝗼𝗯𝗮𝗹\n"
        "  🤍 'stopall  •  'delay <sec>  •  'status\n\n"
        "👑 𝗔𝗱𝗺𝗶𝗻\n"
        "  🤍 'addsudo  •  'delsudo  •  'listsudo\n\n"
        "🎀 𝗜𝗻𝗳𝗼\n"
        "  🤍 'myid  •  'ping\n\n"
        "🎀💅🏻🤍💅🏻🎀💅🏻🤍💅🏻🎀"
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
    # Stop all group_tasks (gcnc, ncemo, impact, long, flood, ist)
    if chat_id in group_tasks:
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
        await update.message.reply_text("⚠️ Reply to a user or provide ID: 'addsudo <id>")

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
        await update.message.reply_text("⚠️ Reply to a user or provide ID: 'delsudo <id>")

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
    try:
        reactions = [ReactionTypeEmoji(emoji=e) for e in react_emojis[chat_id]]
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=msg.message_id,
            reaction=reactions,
        )
    except Exception as e:
        print(f"[WARN] React error: {e}")

@only_sudo
async def react_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: 'react <emoji> <emoji> ...")
    chat_id = update.message.chat_id
    react_emojis[chat_id] = list(context.args)
    await update.message.reply_text(f"💬 React mode on  {'  '.join(context.args)}")

@only_sudo
async def stopreact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    react_emojis.pop(chat_id, None)
    await update.message.reply_text("🛑 React mode off.")

# ---------------------------
# PREFIX DISPATCHER  (trigger: ' instead of /)
# ---------------------------
CMD_PREFIX = "'"

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
    
    for token in TOKENS:
        try:
            app = (
                Application.builder()
                .token(token)
                .concurrent_updates(True)
                .connect_timeout(20)
                .read_timeout(20)
                .write_timeout(20)
                .build()
            )
            app.add_handler(MessageHandler(filters.TEXT, prefix_handler), group=0)
            app.add_handler(MessageHandler(filters.ALL, react_handler), group=1)
            apps.append(app)
            bots.append(app.bot)
            print(f"  ✅  Bot loaded : {token[:22]}...", flush=True)
        except Exception as e:
            print(f"  ❌  Failed     : {token[:22]}...  →  {e}", flush=True)
    
    if not apps:
        print("[FATAL] No bots loaded. Exiting.", flush=True)
        return

    print_banner(len(apps))
    
    await asyncio.gather(*[app.initialize() for app in apps])

    print(flush=True)
    print("  🤍  ʙᴏᴛ ʟɪsᴛ", flush=True)
    for i, app in enumerate(apps, 1):
        uname = app.bot.username or "unknown"
        print(f"      {i:>2}. @{uname}", flush=True)
    print(flush=True)

    await asyncio.gather(*[app.start() for app in apps])
    await asyncio.gather(*[
        app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message"],
            timeout=30,
        )
        for app in apps
    ])
    
    print("  🟢  All bots polling — prefix: '\n", flush=True)
    
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
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except Exception as e:
                print(f"[WARN] Shutdown error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
