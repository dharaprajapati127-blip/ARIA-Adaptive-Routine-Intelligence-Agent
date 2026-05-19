from dotenv import load_dotenv
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! I'm ARIA — your Adaptive Routine Intelligence Agent.\n\nI'm still being built, but I'll soon be negotiating your day with you. Stay tuned 👀"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Got it: {update.message.text}\n\n(I'm learning to respond properly — come back soon!)")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

print("ARIA is running...")
app.run_polling()
