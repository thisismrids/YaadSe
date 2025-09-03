import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# =========================
# CONFIG
# =========================
TOKEN = "8331278703:AAHPEVqgxd8WDXOLDhxeSFvwdvHF32tVWs8"

# Logging (good for Render logs)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Scheduler
scheduler = AsyncIOScheduler()


# =========================
# HANDLERS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I’m YaadSe.\n\n"
        "Use /remind YYYY-MM-DD HH:MM message\n"
        "Example:\n/remind 2025-09-05 14:30 Go for a walk 🚶"
    )


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /remind YYYY-MM-DD HH:MM message """
    try:
        if len(context.args) < 3:
            await update.message.reply_text(
                "❌ Usage: /remind YYYY-MM-DD HH:MM message"
            )
            return

        date_str = context.args[0]
        time_str = context.args[1]
        message = " ".join(context.args[2:])

        remind_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        # schedule the job
        scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=remind_time),
            args=[update.effective_chat.id, message, context.application],
        )

        await update.message.reply_text(
            f"✅ Reminder set for {remind_time.strftime('%Y-%m-%d %H:%M')}: {message}"
        )

    except ValueError:
        await update.message.reply_text("⚠️ Invalid format. Try again.\nExample: /remind 2025-09-05 14:30 Meeting")


async def send_reminder(chat_id: int, message: str, app):
    """Send the actual reminder message."""
    try:
        await app.bot.send_message(chat_id=chat_id, text=f"🔔 Reminder: {message}")
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")


# =========================
# MAIN
# =========================

def main():
    scheduler.start()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind_command))

    logger.info("Bot started 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()
