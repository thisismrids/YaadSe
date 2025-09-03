import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# --- Setup logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Load Bot Token from Environment ---
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not found. Set it in Render environment variables.")

# --- Scheduler ---
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Namaste! YaadSe is live 🚀")

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set a reminder with /remind <seconds> <message>"""
    try:
        delay = int(context.args[0])
        message = " ".join(context.args[1:])

        if not message:
            await update.message.reply_text("⚠️ Please give a reminder message.")
            return

        chat_id = update.effective_chat.id

        scheduler.add_job(
            send_reminder,
            "date",
            run_date=datetime.now() + timedelta(seconds=delay),
            args=[chat_id, message, context.application],
        )

        await update.message.reply_text(f"✅ Reminder set for {delay} seconds from now!")

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /remind <seconds> <message>")

async def send_reminder(chat_id: int, message: str, app):
    """Send reminder to user"""
    try:
        await app.bot.send_message(chat_id=chat_id, text=f"⏰ Reminder: {message}")
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")

# --- Main Function ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Start the scheduler
    scheduler.start()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))

    logger.info("🚀 YaadSe Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
