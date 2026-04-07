import os
import sqlite3
import re
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================
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

# ================= CACHE =================
cache = {}  # giảm query DB

# ================= APP MAP =================
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

# ================= PARSE =================
def parse_file(doc, caption):
    app_name, version = None, None

    if caption:
        parts = caption.lower().split()
        if len(parts) >= 2:
            app_name, version = parts[0], parts[1]

    if not version and doc.file_name:
        name = doc.file_name.lower()
        match = re.search(r"([a-zA-Z_]+)[ _-]?(\d+(\.\d+)+)", name)
        if match:
            app_name = match.group(1)
            version = match.group(2)

    if app_name:
        app_name = APP_MAP.get(app_name, app_name)

    return app_name, version

# ================= SAFE SEND =================
async def safe_send(func, *args, retries=3):
    for i in range(retries):
        try:
            return await func(*args)
        except Exception as e:
            logging.warning(f"Retry {i+1}: {e}")
            await asyncio.sleep(1)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/get app version\n/list app\n/latest app"
    )

# ================= SAVE FILE =================
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post or update.edited_message
    if not msg or not msg.document:
        return

    doc = msg.document

    app_name, version = parse_file(doc, msg.caption)

    if not app_name or not version:
        return

    key = f"{app_name}:{version}"

    # tránh ghi DB trùng
    if key in cache:
        return

    cache[key] = doc.file_id

    cursor.execute("""
        INSERT OR REPLACE INTO ipa_files (app_name, version, file_id)
        VALUES (?, ?, ?)
    """, (app_name, version, doc.file_id))

    conn.commit()

    logging.info(f"SAVED {key}")

    await asyncio.sleep(0.3)  # giảm rate limit

# ================= GET =================
async def get_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("/get app version")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())
    version = context.args[1]

    key = f"{app}:{version}"

    if key in cache:
        file_id = cache[key]
    else:
        cursor.execute(
            "SELECT file_id FROM ipa_files WHERE app_name=? AND version=?",
            (app, version)
        )
        result = cursor.fetchone()
        if not result:
            await update.message.reply_text("Không có file")
            return
        file_id = result[0]
        cache[key] = file_id

    await safe_send(update.message.reply_document, file_id)

# ================= LIST =================
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
        await update.message.reply_text("\n".join(r[0] for r in rows))
    else:
        await update.message.reply_text("Trống")

# ================= LATEST =================
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
        await safe_send(update.message.reply_document, result[1])
    else:
        await update.message.reply_text("Trống")

# ================= DEBUG =================
async def debug_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT * FROM ipa_files")
    await update.message.reply_text(str(cursor.fetchall()))

# ================= BOT INIT =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("get", get_app))
app.add_handler(CommandHandler("list", list_app))
app.add_handler(CommandHandler("latest", latest))
app.add_handler(CommandHandler("db", debug_db))

# bắt tất cả loại message
app.add_handler(MessageHandler(filters.ALL, save_file))

print("BOT RUNNING")
app.run_polling()
