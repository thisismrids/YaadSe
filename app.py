import logging
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import dateparser
from dateparser.search import search_dates

# ========== CONFIG ==========
import os
TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "reminders.db"
# ============================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- DB Setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            remind_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_reminder(user_id, message, remind_at):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO reminders (user_id, message, remind_at) VALUES (?, ?, ?)",
              (user_id, message, remind_at))
    conn.commit()
    conn.close()

def load_reminders(job_queue):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, message, remind_at FROM reminders")
    for user_id, message, remind_at in c.fetchall():
        try:
            remind_time = datetime.fromisoformat(remind_at)
        except ValueError:
            remind_time = datetime.strptime(remind_at, "%Y-%m-%d %H:%M")

        delay = (remind_time - datetime.now()).total_seconds()
        if delay > 0:
            job_queue.run_once(
                send_reminder,
                when=delay,
                chat_id=user_id,
                data={"message": message}
            )
    conn.close()

def delete_all_reminders(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I’m Your Very Own YaadSe...\n\n"
        "I'll keep everything 'dhyan se' and remind you 'yaad se'\n\n"
    )

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text(
                "⚠️ Usage: /remind <message with time>\n\n"
                "Example:\n/remind me to go shopping at 4pm on 4th Aug 2025"
            )
            return

        text = " ".join(context.args)

        results = search_dates(
            text,
            settings={
                "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": False
            }
        )

        if not results:
            await update.message.reply_text("❌ Sorry, I couldn’t understand the date/time.")
            return

        matched_text, remind_time = results[0]

        if remind_time < datetime.now():
            await update.message.reply_text("❌ That time is in the past. Please choose a future time.")
            return

        message = text.replace(matched_text, "").strip()
        if not message:
            message = "Reminder"

        user_id = update.message.chat_id
        save_reminder(user_id, message, remind_time.isoformat())

        delay = (remind_time - datetime.now()).total_seconds()
        context.job_queue.run_once(
            send_reminder,
            when=delay,
            chat_id=user_id,
            data={"message": message}
        )

        await update.message.reply_text(
            f"✅ Reminder set for {remind_time.strftime('%Y-%m-%d %H:%M')}: {message}"
        )

    except Exception as e:
        await update.message.reply_text("⚠️ Something went wrong.")
        print(e)

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(
        chat_id=job.chat_id,
        text=f"🔔 Reminder: {job.data['message']}"
    )

    # Auto-delete reminder from DB once sent
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE user_id = ? AND message = ?",
              (job.chat_id, job.data["message"]))
    conn.commit()
    conn.close()

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, message, remind_at FROM reminders WHERE user_id = ?", (update.message.chat_id,))
    reminders = c.fetchall()
    conn.close()

    if not reminders:
        await update.message.reply_text("📭 No reminders set.")
        return

    text = "📝 Your reminders:\n\n"
    for i, (rid, msg, when) in enumerate(reminders, start=1):
        text += f"{i}. {msg} ⏰ {when}\n"

    await update.message.reply_text(text)

# --- Delete Reminders ---
DELETE_CHOICE = 1

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, message, remind_at FROM reminders WHERE user_id = ?", (update.message.chat_id,))
    reminders = c.fetchall()
    conn.close()

    if not reminders:
        await update.message.reply_text("📭 No reminders to delete.")
        return ConversationHandler.END

    context.user_data["reminders_to_delete"] = reminders

    reminder_list = "\n".join(
        [f"{i+1}. {msg} ⏰ {when}" for i, (rid, msg, when) in enumerate(reminders)]
    )

    await update.message.reply_text(
        "🗑 Which reminder do you want to delete?\n\n"
        f"{reminder_list}\n\nReply with the number (e.g., 1)"
    )
    return DELETE_CHOICE

async def delete_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = context.user_data.get("reminders_to_delete", [])
    try:
        choice = int(update.message.text) - 1
        if 0 <= choice < len(reminders):
            rid, msg, when = reminders[choice]

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM reminders WHERE id = ?", (rid,))
            conn.commit()
            conn.close()

            await update.message.reply_text(f"✅ Deleted reminder: {msg} ⏰ {when}")
        else:
            await update.message.reply_text("❌ Invalid number. Please try again.")
            return DELETE_CHOICE
    except ValueError:
        await update.message.reply_text("❌ Please send a valid number.")
        return DELETE_CHOICE

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Delete cancelled.")
    return ConversationHandler.END

# --- Clear all reminders ---
async def clear_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    delete_all_reminders(user_id)

    if context.job_queue:
        for job in context.job_queue.jobs():
            if job.chat_id == user_id:
                job.schedule_removal()

    await update.message.reply_text("🗑️ All your reminders have been cleared.")

# --- Main ---
def main():
    init_db()

    app = Application.builder().token(TOKEN).build()
    job_queue = app.job_queue

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("list", list_reminders))

    delete_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_command)],
        states={
            DELETE_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_choice)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(delete_conv_handler)

    app.add_handler(CommandHandler("clearreminders", clear_reminders))

    load_reminders(job_queue)

    print("🤖 YaadSe Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
