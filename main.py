"""
ARIA — Adaptive Routine Intelligence Agent
main.py

Changes in his version:
  - Task limit set during onboarding (user picks 3 / 5 / custom)
  - Task reminders only show incomplete tasks
  - Motivational messages after task completion
  - Checkin prompt tells user how many tasks they can set
  - /setalarm also allows changing task limit
"""

import logging
import re
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import os

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import database as db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Motivational messages
# ─────────────────────────────────────────────────────────────
MOTIVATION_SINGLE = [
    "One down. Keep that momentum going! 🔥",
    "That's how it's done. One step closer! 💪",
    "Checked off. You're building something real today.",
    "Done! Small wins add up to big results. 🎯",
    "Nice work. Stay locked in! 🚀",
    "That's discipline. Keep going! ⚡",
    "One less thing standing between you and a great day. 💥",
]

MOTIVATION_ALL_DONE = [
    "ALL TASKS DONE! 🏆 That's a full day. You crushed it.",
    "Everything's checked off. This is what consistency looks like. 🔥",
    "Complete. Rest well tonight — you earned it. 🌙",
    "All done! This is who you're becoming. Keep showing up. 💪",
    "Full completion. Most people won't do what you just did. 🎯",
]

def get_motivation(all_done: bool) -> str:
    if all_done:
        return random.choice(MOTIVATION_ALL_DONE)
    return random.choice(MOTIVATION_SINGLE)


# ─────────────────────────────────────────────────────────────
# Conversation states
# ─────────────────────────────────────────────────────────────
OB_WAKE, OB_SLEEP, OB_GOAL, OB_TASKS_LIMIT, OB_GAP = range(5)
SLEEP_IN, ENERGY, TASKS = range(10, 13)
SA_WHICH, SA_VALUE = range(20, 22)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def parse_time(text: str) -> str | None:
    text = text.strip().upper().replace(".", ":")
    patterns = [
        r"^(\d{1,2}):(\d{2})\s*(AM|PM)?$",
        r"^(\d{1,2})\s*(AM|PM)$",
        r"^(\d{1,2}):(\d{2})$",
    ]
    for pat in patterns:
        m = re.match(pat, text)
        if m:
            g = m.groups()
            hour   = int(g[0])
            minute = int(g[1]) if len(g) > 1 and g[1] and g[1].isdigit() else 0
            ampm   = g[-1] if g[-1] in ("AM", "PM") else None
            if ampm == "PM" and hour != 12: hour += 12
            elif ampm == "AM" and hour == 12: hour = 0
            if 0 <= hour < 24 and 0 <= minute < 60:
                return f"{hour:02d}:{minute:02d}"
    return None


def fmt_tasks(tasks: list[str]) -> str:
    return "\n".join(f"  {i+1}. {t}" for i, t in enumerate(tasks))


# ─────────────────────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────────────────────
def schedule_user_alarms(app, user: dict, scheduler: AsyncIOScheduler) -> None:
    uid = user["telegram_id"]
    tz  = ZoneInfo(user.get("timezone") or "Asia/Kolkata")

    for job_id in [f"wake_{uid}", f"sleep_{uid}", f"tasks_{uid}"]:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

    if user.get("wake_time"):
        wh, wm = map(int, user["wake_time"].split(":"))
        scheduler.add_job(
            send_wake_alarm, CronTrigger(hour=wh, minute=wm, timezone=tz),
            id=f"wake_{uid}", kwargs={"app": app, "uid": uid}, replace_existing=True,
        )

    if user.get("sleep_time"):
        sh, sm = map(int, user["sleep_time"].split(":"))
        scheduler.add_job(
            send_sleep_alarm, CronTrigger(hour=sh, minute=sm, timezone=tz),
            id=f"sleep_{uid}", kwargs={"app": app, "uid": uid}, replace_existing=True,
        )

    gap = user.get("task_reminder_gap") or 90
    if user.get("wake_time") and user.get("sleep_time"):
        wh, wm = map(int, user["wake_time"].split(":"))
        now    = datetime.now(tz)
        start  = now.replace(hour=wh, minute=wm, second=0, microsecond=0)
        if start < now:
            start += timedelta(days=1)
        scheduler.add_job(
            send_task_reminder, "interval", minutes=gap, start_date=start,
            id=f"tasks_{uid}", kwargs={"app": app, "uid": uid}, replace_existing=True,
        )


# ─────────────────────────────────────────────────────────────
# Alarm senders
# ─────────────────────────────────────────────────────────────
async def send_wake_alarm(app, uid: int) -> None:
    user = db.get_user(uid)
    name = (user or {}).get("first_name") or "there"
    await app.bot.send_message(
        chat_id=uid,
        text=f"⏰ Good morning, {name}!\n\nTime to rise and conquer the day. 🌅\nType /checkin to set up your ARIA plan.",
    )


async def send_sleep_alarm(app, uid: int) -> None:
    user = db.get_user(uid)
    name = (user or {}).get("first_name") or "there"
    goal = (user or {}).get("sleep_goal_hours")
    goal_str = f"You need {goal}h — make it count." if goal else "Give yourself enough rest."
    await app.bot.send_message(
        chat_id=uid,
        text=f"🌙 Hey {name}, time to wind down.\n\n{goal_str}\n\nPut the phone down. Tomorrow needs you fresh 💤",
    )


async def send_task_reminder(app, uid: int) -> None:
    completions = db.get_task_completions(uid)
    if not completions:
        return

    incomplete = [c for c in completions if not c["completed"]]
    if not incomplete:
        return  # all done, stay quiet

    done_count = len(completions) - len(incomplete)
    progress = f"({done_count}/{len(completions)} done) " if done_count > 0 else ""
    tasks_str = "\n".join(f"  {c['task_index']+1}. {c['task_text']}" for c in incomplete)

    await app.bot.send_message(
        chat_id=uid,
        text=(
            f"📋 Task check-in! {progress}\n\n"
            f"Still pending:\n{tasks_str}\n\n"
            "Use /done <number> to mark one complete."
        ),
    )


# ─────────────────────────────────────────────────────────────
# post_init
# ─────────────────────────────────────────────────────────────
async def post_init(app) -> None:
    scheduler = AsyncIOScheduler()
    scheduler.start()
    app.bot_data["scheduler"] = scheduler

    users = db.get_all_onboarded_users()
    for user in users:
        schedule_user_alarms(app, user, scheduler)
    logger.info(f"[ARIA] Restored alarms for {len(users)} user(s).")


# ─────────────────────────────────────────────────────────────
# /start → onboarding
# ─────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_user = update.effective_user
    db.upsert_user(tg_user.id, tg_user.username, tg_user.first_name)
    user = db.get_user(tg_user.id)

    if user and user.get("onboarded"):
        await update.message.reply_text(
            f"Hey {tg_user.first_name}! Welcome back 👋\n\n"
            "Type /checkin to plan your day, or /alarms to see your schedule."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"Hey {tg_user.first_name}! I'm ARIA 🤖 — your Adaptive Routine Intelligence Agent.\n\n"
        "Quick 30-second setup and I'll handle your reminders forever.\n\n"
        "⏰ What time do you usually *wake up*?\n_(e.g. 6:30am, 7am, 08:00)_",
        parse_mode="Markdown",
    )
    return OB_WAKE


async def ob_get_wake(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = parse_time(update.message.text)
    if not t:
        await update.message.reply_text("Try something like *7am* or *07:30*", parse_mode="Markdown")
        return OB_WAKE
    context.user_data["wake_time"] = t
    await update.message.reply_text(
        f"Wake at *{t}* ✅\n\n🌙 What time do you want to *go to sleep*?\n_(e.g. 11pm, 23:30)_",
        parse_mode="Markdown",
    )
    return OB_SLEEP


async def ob_get_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = parse_time(update.message.text)
    if not t:
        await update.message.reply_text("Try something like *11pm* or *23:00*", parse_mode="Markdown")
        return OB_SLEEP
    context.user_data["sleep_time"] = t
    await update.message.reply_text(
        f"Sleep at *{t}* ✅\n\n😴 What's your sleep *goal* in hours?\n_(e.g. 7, 7.5, 8)_",
        parse_mode="Markdown",
    )
    return OB_GOAL


async def ob_get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace("h", "").replace("hours", "").strip()
    try:
        hours = float(text)
        assert 3 <= hours <= 12
    except Exception:
        await update.message.reply_text("Enter a number between 3 and 12, like *8* or *7.5*", parse_mode="Markdown")
        return OB_GOAL
    context.user_data["sleep_goal_hours"] = hours

    keyboard = [["3 tasks", "5 tasks", "Custom"]]
    await update.message.reply_text(
        f"Goal: *{hours}h* ✅\n\n📌 How many tasks do you want to set *per day*?\n\n"
        "This keeps your focus sharp — don't overload yourself.",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown",
    )
    return OB_TASKS_LIMIT


async def ob_get_tasks_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    mapping = {"3 tasks": 3, "5 tasks": 5}
    limit = mapping.get(text)
    if not limit:
        try:
            limit = int(re.search(r"\d+", text).group())
            assert 1 <= limit <= 10
        except Exception:
            await update.message.reply_text(
                "Enter a number between 1 and 10, or pick from the options.",
                reply_markup=ReplyKeyboardMarkup(
                    [["3 tasks", "5 tasks", "Custom"]], one_time_keyboard=True, resize_keyboard=True
                ),
            )
            return OB_TASKS_LIMIT

    context.user_data["task_limit"] = limit

    keyboard = [["30 min", "60 min", "90 min", "2 hours"]]
    await update.message.reply_text(
        f"*{limit} tasks/day* ✅\n\n📋 How often should I *remind you about your tasks* during the day?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown",
    )
    return OB_GAP


async def ob_get_gap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    mapping = {"30 min": 30, "60 min": 60, "90 min": 90, "2 hours": 120}
    gap = mapping.get(text)
    if not gap:
        try:
            gap = int(re.search(r"\d+", text).group())
        except Exception:
            gap = 90

    uid   = update.effective_user.id
    limit = context.user_data.get("task_limit", 3)

    db.save_user_prefs(
        uid,
        wake_time=context.user_data["wake_time"],
        sleep_time=context.user_data["sleep_time"],
        sleep_goal_hours=context.user_data["sleep_goal_hours"],
        task_reminder_gap=gap,
        task_limit=limit,
        onboarded=True,
    )
    user = db.get_user(uid)

    scheduler: AsyncIOScheduler = context.application.bot_data["scheduler"]
    schedule_user_alarms(context.application, user, scheduler)

    await update.message.reply_text(
        f"✅ *All set! Your ARIA schedule:*\n\n"
        f"⏰ Wake alarm:       *{user['wake_time']}*\n"
        f"🌙 Sleep alarm:      *{user['sleep_time']}*\n"
        f"😴 Sleep goal:       *{user['sleep_goal_hours']}h*\n"
        f"📌 Tasks per day:    *{limit}*\n"
        f"📋 Task reminders:   every *{gap} min*\n\n"
        "Type /checkin each morning to plan your day.\n"
        "Use /setalarm to change any of these anytime.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# /checkin — daily morning flow
# ─────────────────────────────────────────────────────────────
async def checkin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid  = update.effective_user.id
    user = db.get_user(uid)
    if not user or not user.get("onboarded"):
        await update.message.reply_text("Let's set you up first! Type /start")
        return ConversationHandler.END

    existing = db.get_todays_checkin(uid)
    if existing and existing.get("tasks"):
        tasks = existing["tasks"]
        completions = db.get_task_completions(uid)
        lines = []
        for c in completions:
            mark = "✅" if c["completed"] else "⬜"
            lines.append(f"{mark} {c['task_index']+1}. {c['task_text']}")
        await update.message.reply_text(
            f"You've already checked in today ✅\n\n"
            f"⚡ Energy: {existing.get('energy_level', '?')}\n\n"
            f"📌 Tasks:\n" + "\n".join(lines) +
            "\n\nUse /done <number> to mark tasks complete."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Good morning! 🌤 Let's plan your day.\n\n"
        "What time did you *sleep* and *wake up* today?\n"
        "_(e.g. slept 1am, woke 7:30am)_",
        parse_mode="Markdown",
    )
    return SLEEP_IN


async def get_sleep_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["sleep"] = update.message.text
    db.save_checkin(update.effective_user.id, sleep_time=update.message.text)
    keyboard = [["High 🔥", "Medium ⚡", "Low 🌙"]]
    await update.message.reply_text(
        "Got it! How's your energy right now?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ENERGY


async def get_energy_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["energy"] = update.message.text
    db.save_checkin(update.effective_user.id, energy_level=update.message.text)
    uid   = update.effective_user.id
    user  = db.get_user(uid)
    limit = user.get("task_limit") or 3
    await update.message.reply_text(
        f"What are your top *{limit} tasks* for today?\n_(One per line)_",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    return TASKS


async def get_tasks_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid   = update.effective_user.id
    user  = db.get_user(uid)
    limit = user.get("task_limit") or 3

    raw   = update.message.text.strip()
    tasks = [
        re.sub(r"^[\d]+[.)]\s*", "", line).strip()
        for line in raw.splitlines() if line.strip()
    ][:limit]

    db.save_checkin(uid, tasks=tasks)

    energy = context.user_data.get("energy", "?")
    goal   = user.get("sleep_goal_hours")

    summary = (
        f"📋 *ARIA Summary*\n\n"
        f"😴 Sleep: {context.user_data.get('sleep', '?')}\n"
        f"⚡ Energy: {energy}\n"
    )
    if goal:
        summary += f"🎯 Sleep goal tonight: *{goal}h* (alarm at {user['sleep_time']})\n"
    summary += (
        f"\n📌 Tasks:\n{fmt_tasks(tasks)}\n\n"
        f"I'll remind you every {user.get('task_reminder_gap', 90)} min "
        f"and ping you at {user.get('sleep_time', '?')} to wind down.\n\n"
        "Let's make today count! 💪\n"
        "Use /done <number> to mark a task complete."
    )
    await update.message.reply_text(summary, parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# /setalarm
# ─────────────────────────────────────────────────────────────
async def setalarm_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["⏰ Wake-up", "🌙 Sleep"], ["📋 Task reminder gap", "📌 Task limit"]]
    await update.message.reply_text(
        "Which setting do you want to change?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return SA_WHICH


async def setalarm_which(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if "Wake" in text:
        context.user_data["alarm_type"] = "wake"
        prompt = "Enter your new *wake-up time* (e.g. 6:30am)"
    elif "Sleep" in text:
        context.user_data["alarm_type"] = "sleep"
        prompt = "Enter your new *sleep time* (e.g. 11pm)"
    elif "limit" in text.lower():
        context.user_data["alarm_type"] = "limit"
        prompt = "How many tasks per day? (enter a number between 1 and 10)"
    else:
        context.user_data["alarm_type"] = "gap"
        prompt = "How many minutes between task reminders? (e.g. 60)"
    await update.message.reply_text(prompt, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    return SA_VALUE


async def setalarm_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid        = update.effective_user.id
    alarm_type = context.user_data.get("alarm_type")
    text       = update.message.text.strip()

    if alarm_type in ("wake", "sleep"):
        t = parse_time(text)
        if not t:
            await update.message.reply_text("Couldn't read that. Try again (e.g. 7am or 23:00)")
            return SA_VALUE
        if alarm_type == "wake":
            db.save_user_prefs(uid, wake_time=t)
            msg = f"⏰ Wake alarm updated to *{t}* ✅"
        else:
            db.save_user_prefs(uid, sleep_time=t)
            msg = f"🌙 Sleep alarm updated to *{t}* ✅"

    elif alarm_type == "limit":
        try:
            limit = int(re.search(r"\d+", text).group())
            assert 1 <= limit <= 10
        except Exception:
            await update.message.reply_text("Enter a number between 1 and 10.")
            return SA_VALUE
        db.save_user_prefs(uid, task_limit=limit)
        msg = f"📌 Task limit updated to *{limit} tasks/day* ✅"

    else:
        try:
            gap = int(re.search(r"\d+", text).group())
            assert 15 <= gap <= 480
        except Exception:
            await update.message.reply_text("Enter minutes between 15 and 480.")
            return SA_VALUE
        db.save_user_prefs(uid, task_reminder_gap=gap)
        msg = f"📋 Task reminders set to every *{gap} min* ✅"

    user = db.get_user(uid)
    scheduler: AsyncIOScheduler = context.application.bot_data["scheduler"]
    schedule_user_alarms(context.application, user, scheduler)
    await update.message.reply_text(msg, parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# /alarms
# ─────────────────────────────────────────────────────────────
async def alarms_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = db.get_user(update.effective_user.id)
    if not user or not user.get("onboarded"):
        await update.message.reply_text("Run /start first to set up your schedule.")
        return
    await update.message.reply_text(
        f"⏰ *Your ARIA Settings*\n\n"
        f"Wake-up:         *{user.get('wake_time') or 'not set'}*\n"
        f"Sleep:           *{user.get('sleep_time') or 'not set'}*\n"
        f"Sleep goal:      *{user.get('sleep_goal_hours') or 'not set'}h*\n"
        f"Tasks per day:   *{user.get('task_limit', 3)}*\n"
        f"Task reminders:  every *{user.get('task_reminder_gap', 90)} min*\n\n"
        "Use /setalarm to change any of these.",
        parse_mode="Markdown",
    )


# ─────────────────────────────────────────────────────────────
# /done
# ─────────────────────────────────────────────────────────────
async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid     = update.effective_user.id
    checkin = db.get_todays_checkin(uid)
    tasks   = (checkin or {}).get("tasks") or []

    if not tasks:
        await update.message.reply_text("No tasks yet. Do /checkin first!")
        return

    if context.args:
        try:
            idx = int(context.args[0]) - 1
            if db.mark_task_done(uid, idx):
                # Check if all tasks are now done
                completions = db.get_task_completions(uid)
                all_done = all(c["completed"] for c in completions)
                motivation = get_motivation(all_done)

                await update.message.reply_text(
                    f"✅ *Done:* _{tasks[idx]}_\n\n{motivation}",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text("Already marked done, or task not found.")
        except (ValueError, IndexError):
            await update.message.reply_text(f"Use /done 1 to /done {len(tasks)}.")
    else:
        completions = db.get_task_completions(uid)
        lines = []
        for c in completions:
            mark = "✅" if c["completed"] else "⬜"
            lines.append(f"{mark} {c['task_index']+1}. {c['task_text']}")
        done_count = sum(1 for c in completions if c["completed"])
        await update.message.reply_text(
            f"📋 *Today's tasks* ({done_count}/{len(completions)} done):\n\n" +
            "\n".join(lines) +
            "\n\nUse /done 1, /done 2, etc. to mark complete."
            , parse_mode="Markdown"
        )


# ─────────────────────────────────────────────────────────────
# /history
# ─────────────────────────────────────────────────────────────
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = db.get_checkin_history(update.effective_user.id, limit=5)
    if not rows:
        await update.message.reply_text("No check-in history yet. Do /checkin to start!")
        return
    lines = ["📅 *Last 5 check-ins*\n"]
    for r in rows:
        date_str = str(r["checkin_date"])
        energy   = r.get("energy_level") or "?"
        lines.append(f"*{date_str}* — Energy: {energy}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────
# /cancel
# ─────────────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Cancelled. Type /checkin whenever you're ready!",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────
def main() -> None:
    db.init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    onboarding = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            OB_WAKE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_get_wake)],
            OB_SLEEP:       [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_get_sleep)],
            OB_GOAL:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_get_goal)],
            OB_TASKS_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_get_tasks_limit)],
            OB_GAP:         [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_get_gap)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    checkin = ConversationHandler(
        entry_points=[CommandHandler("checkin", checkin_start)],
        states={
            SLEEP_IN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sleep_checkin)],
            ENERGY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_energy_checkin)],
            TASKS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tasks_checkin)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    setalarm = ConversationHandler(
        entry_points=[CommandHandler("setalarm", setalarm_start)],
        states={
            SA_WHICH: [MessageHandler(filters.TEXT & ~filters.COMMAND, setalarm_which)],
            SA_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setalarm_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(onboarding)
    app.add_handler(checkin)
    app.add_handler(setalarm)
    app.add_handler(CommandHandler("alarms", alarms_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("history", history_command))

    logger.info("ARIA is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
