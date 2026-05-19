from dotenv import load_dotenv
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# conversation states
SLEEP, ENERGY, TASKS = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! I'm ARIA — your Adaptive Routine Intelligence Agent.\n\nType /checkin to start your day. 🌅"
    )

async def checkin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Good morning! Let's plan your day. 🌤\n\nWhat time did you sleep and wake up today?\n\n(Example: slept 1am, woke 8am)"
    )
    return SLEEP

async def get_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sleep"] = update.message.text
    keyboard = [["High 🔥", "Medium ⚡", "Low 🌙"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Got it! How's your energy level today?",
        reply_markup=reply_markup
    )
    return ENERGY

async def get_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["energy"] = update.message.text
    await update.message.reply_text(
        "Perfect! What are your top 3 tasks for today?\n\n(Just type them out, one per line)",
        reply_markup=ReplyKeyboardRemove()
    )
    return TASKS

async def get_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tasks"] = update.message.text
    sleep = context.user_data["sleep"]
    energy = context.user_data["energy"]
    tasks = context.user_data["tasks"]

    await update.message.reply_text(
        f"Here's your ARIA summary for today 📋\n\n"
        f"😴 Sleep: {sleep}\n"
        f"⚡ Energy: {energy}\n"
        f"📌 Tasks:\n{tasks}\n\n"
        f"I've got your plan ready. Let's make today count! 💪\n\n"
        f"Type /done when you finish a task."
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Check-in cancelled. Type /checkin whenever you're ready!")
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("checkin", checkin_start)],
    states={
        SLEEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sleep)],
        ENERGY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_energy)],
        TASKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tasks)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)

print("ARIA is running...")
app.run_polling()
