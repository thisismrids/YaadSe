import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

DB_FILE = "reminders.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            remind_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I’m YaadSe — your reminder bot.\n\n"
        "Use /remind <minutes> <message> to set a reminder.\n"
        "Example: /remind 10 Drink water 💧"
    )

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(context.args[0])
        message = " ".join(context.args[1:])
        remind_at = datetime.now() + timedelta(minutes=minutes)

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO reminders (chat_id, message, remind_at) VALUES (?, ?, ?)",
                  (update.effective_chat.id, message, remind_at.isoformat()))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Reminder set for {minutes} minutes from now!")

        context.job_queue.run_once(
            send_reminder,
            when=minutes * 60,
            chat_id=update.effective_chat.id,
            data=message
        )

    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /remind <minutes> <message>")

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"⏰ Reminder: {job.data}")

def load_reminders(app):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_id, message, remind_at FROM reminders")
    rows = c.fetchall()
    conn.close()

    now = datetime.now()
    for chat_id, message, remind_at_str in rows:
        remind_at = datetime.fromisoformat(remind_at_str)
        delay = (remind_at - now).total_seconds()
        if delay > 0:
            app.job_queue.run_once(
                send_reminder,
                when=delay,
                chat_id=chat_id,
                data=message
            )

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("⚠️ BOT_TOKEN environment variable not set!")

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))

    load_reminders(app)

    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
