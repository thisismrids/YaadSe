import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
TOKEN = os.getenv("8331278703:AAHPEVqgxd8WDXOLDhxeSFvwdvHF32tVWs8")

# In-memory reminder store
reminders = {}

# ---------------- COMMAND HANDLERS ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    await update.message.reply_text(
        "👋 Hello! I’m YaadSe – your personal reminder bot.\n\n"
        "Commands:\n"
        "/addreminder <time in HH:MM> <task> – add a reminder\n"
        "/listreminders – see your reminders\n"
        "/help – show this message again"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    await update.message.reply_text(
        "Commands:\n"
        "/addreminder <time in HH:MM> <task>\n"
        "/listreminders\n"
        "/help"
    )

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a reminder"""
    try:
        chat_id = update.message.chat_id
        args = context.args

        if len(args) < 2:
            await update.message.reply_text("⚠️ Usage: /addreminder 14:30 Take medicine")
            return

        time_str = args[0]
        task = " ".join(args[1:])

        reminder_time = datetime.strptime(time_str, "%H:%M").time()

        if chat_id not in reminders:
            reminders[chat_id] = []

        reminders[chat_id].append((reminder_time, task))
        await update.message.reply_text(f"✅ Reminder set at {time_str} for: {task}")

    except ValueError:
        await update.message.reply_text("⚠️ Time format should be HH:MM (24-hour).")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List reminders"""
    chat_id = update.message.chat_id
    if chat_id not in reminders or not reminders[chat_id]:
        await update.message.reply_text("📭 You don’t have any reminders yet.")
        return

    text = "📝 Your reminders:\n"
    for rtime, task in reminders[chat_id]:
        text += f"⏰ {rtime.strftime('%H:%M')} – {task}\n"
    await update.message.reply_text(text)

# ---------------- REMINDER CHECKER ---------------- #

async def check_reminders(app):
    """Check reminders and send alerts"""
    now = datetime.now().time().replace(second=0, microsecond=0)
    for chat_id, user_reminders in reminders.items():
        for rtime, task in user_reminders:
            if rtime == now:
                try:
                    await app.bot.send_message(chat_id=chat_id, text=f"⏰ Reminder: {task}")
                except Exception as e:
                    logger.error(f"Error sending reminder: {e}")

# ---------------- MAIN ---------------- #

def main():
    logger.info("Starting YaadSe Bot…")

    # Scheduler
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.start()

    # Build Application
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addreminder", add_reminder))
    app.add_handler(CommandHandler("listreminders", list_reminders))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_command))

    # Schedule reminder check every minute
    scheduler.add_job(lambda: app.create_task(check_reminders(app)), "interval", minutes=1)

    # Run bot
    app.run_polling()

if __name__ == "__main__":
    main()
