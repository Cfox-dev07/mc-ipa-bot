import os
import sqlite3
import re
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================== CONFIG ==================
TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)

# ================== DATABASE ==================
conn = sqlite3.connect("ipa.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS ipa_files (
    app_name TEXT,
    version TEXT,
    file_id TEXT,
    PRIMARY KEY (app_name, version)
)
""")
conn.commit()

# ================== APP MAP ==================
APP_MAP = {
    "minecraft": "minecraft",
    "mc": "minecraft",

    "gta": "gta_sa",
    "gta_sa": "gta_sa",
    "sanandreas": "gta_sa",

    "gtavc": "gta_vc",
    "vicecity": "gta_vc",

    "shadowrocket": "shadowrocket",
    "rocket": "shadowrocket"
}

# ================== PARSE FILE ==================
def parse_file(doc, caption):
    app_name = None
    version = None

    # 1. từ caption
    if caption:
        parts = caption.lower().split()
        if len(parts) >= 2:
            app_name = parts[0]
            version = parts[1]

    # 2. từ file name
    if not version and doc.file_name:
        name = doc.file_name.lower()

        match = re.search(r"([a-zA-Z_]+)[ _-]?(\d+(\.\d+)+)", name)
        if match:
            app_name = match.group(1)
            version = match.group(2)

    if app_name:
        app_name = APP_MAP.get(app_name, app_name)

    return app_name, version

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "IPA BOT\n\n"
        "/get app version\n"
        "/list app\n"
        "/latest app\n\n"
        "Ví dụ:\n"
        "/get minecraft 1.20.1"
    )

# ================== SAVE FILE ==================
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message

        if not msg or not msg.document:
            return

        doc = msg.document
        app_name, version = parse_file(doc, msg.caption)

        logging.info(f"RAW: {app_name} {version}")

        if not app_name or not version:
            logging.info("Parse fail")
            return

        cursor.execute("""
            INSERT OR REPLACE INTO ipa_files (app_name, version, file_id)
            VALUES (?, ?, ?)
        """, (app_name, version, doc.file_id))

        conn.commit()

        logging.info(f"SAVED: {app_name} {version}")

    except Exception as e:
        logging.error(f"ERROR: {e}")

# ================== GET ==================
async def get_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("/get app version")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())
    version = context.args[1]

    cursor.execute(
        "SELECT file_id FROM ipa_files WHERE app_name=? AND version=?",
        (app, version)
    )
    result = cursor.fetchone()

    if result:
        await update.message.reply_document(result[0])
    else:
        await update.message.reply_text("Không có file")

# ================== LIST ==================
async def list_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("/list app")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())

    cursor.execute(
        "SELECT version FROM ipa_files WHERE app_name=? ORDER BY version",
        (app,)
    )
    rows = cursor.fetchall()

    if rows:
        text = "\n".join([r[0] for r in rows])
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("Trống")

# ================== LATEST ==================
async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("/latest app")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())

    cursor.execute(
        "SELECT version, file_id FROM ipa_files WHERE app_name=? ORDER BY version DESC LIMIT 1",
        (app,)
    )
    result = cursor.fetchone()

    if result:
        await update.message.reply_document(result[1])
    else:
        await update.message.reply_text("Trống")

# ================== DEBUG DB ==================
async def debug_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT * FROM ipa_files")
    rows = cursor.fetchall()
    await update.message.reply_text(str(rows))

# ================== BOT INIT ==================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("get", get_app))
app.add_handler(CommandHandler("list", list_app))
app.add_handler(CommandHandler("latest", latest))
app.add_handler(CommandHandler("db", debug_db))

# FIX: bắt file trong group + private
app.add_handler(MessageHandler(filters.Document.ALL, save_file))

print("BOT RUNNING...")
app.run_polling()
