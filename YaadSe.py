import os
import asyncio
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ---------------- Database Setup ---------------- #
DB_FILE = "reminders.db"

def init_db():
    """Ensure the reminders table exists with correct schema."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        remind_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

# ---------------- Helper Functions ---------------- #
def save_reminder(user_id, message, remind_at):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO reminders (user_id, message, remind_at) VALUES (?, ?, ?)",
              (user_id, message, remind_at))
    conn.commit()
    conn.close()

def delete_reminder(user_id, message):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE user_id = ? AND message = ?", (user_id, message))
    conn.commit()
    conn.close()

def get_all_reminders():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, user_id, message, remind_at FROM reminders")
    rows = c.fetchall()
    conn.close()
    return rows

# ---------------- Bot Handlers ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I’m YaadSe Bot.\n\n"
        "Commands:\n"
        "🔹 /remind <YYYY-MM-DD HH:MM> <message>\n"
        "🔹 /list - Show all reminders\n"
        "🔹 /delete <message> - Delete a reminder\n"
    )

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        date_str = context.args[0] + " " + context.args[1]  # "YYYY-MM-DD HH:MM"
        remind_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        message = " ".join(context.args[2:])

        save_reminder(user_id, message, remind_time.isoformat())

        # Schedule job
        context.job_queue.run_once(
            send_reminder,
            when=(remind_time - datetime.now()).total_seconds(),
            chat_id=update.message.chat_id,
            name=f"reminder-{user_id}-{message}",
            data={"user_id": user_id, "message": message}
        )

        await update.message.reply_text(f"✅ Reminder set for {remind_time} : {message}")

    except Exception as e:
        await update.message.reply_text("❌ Usage: /remind YYYY-MM-DD HH:MM <message>")
        print(e)

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"⏰ Reminder: {job.data['message']}")
    delete_reminder(job.data["user_id"], job.data["message"])

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = get_all_reminders()
    if not reminders:
        await update.message.reply_text("📭 No reminders set.")
        return

    text = "📝 Your reminders:\n"
    for r in reminders:
        text += f"- {r[3]} : {r[2]}\n"
    await update.message.reply_text(text)

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /delete <message>")
        return
    message = " ".join(context.args)
    user_id = update.message.from_user.id
    delete_reminder(user_id, message)
    await update.message.reply_text(f"🗑 Deleted reminder: {message}")

# ---------------- Main ---------------- #
def main():
    init_db()

    TOKEN = "8331278703:AAHPEVqgxd8WDXOLDhxeSFvwdvHF32tVWs8"  # your token
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("delete", delete_command))

    # Reload old reminders
    for _id, user_id, message, remind_at in get_all_reminders():
        remind_time = datetime.fromisoformat(remind_at)
        if remind_time > datetime.now():
            app.job_queue.run_once(
                send_reminder,
                when=(remind_time - datetime.now()).total_seconds(),
                chat_id=user_id,
                name=f"reminder-{user_id}-{message}",
                data={"user_id": user_id, "message": message}
            )

    print("🤖 YaadSe Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
