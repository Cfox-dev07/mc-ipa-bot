import os
import sqlite3
import re
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# ================= LOG =================
logging.basicConfig(level=logging.INFO)

# ================= TOKEN =================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN chưa được set")

# ================= DB =================
conn = sqlite3.connect("ipa.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS ipa_files (
    app_name TEXT,
    version TEXT,
    file_id TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (app_name, version)
)
""")
conn.commit()

# ================= MAP APP =================
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

# ================= ADMIN (tuỳ chọn) =================
ADMIN_ID = None  # điền Telegram ID của bạn nếu muốn khóa upload

# ================= HELP =================
async def start(update, context):
    await update.message.reply_text(
        "📦 IPA BOT\n\n"
        "/get app version\n"
        "/list app\n"
        "/latest app\n"
        "/search keyword\n"
    )

# ================= PARSE =================
def parse_file(doc, caption):
    app_name = None
    version = None

    # caption
    if caption:
        parts = caption.lower().split()
        if len(parts) >= 2:
            app_name, version = parts[0], parts[1]

    # filename
    if not version and doc.file_name:
        name = doc.file_name.lower()

        match = re.search(r"([a-zA-Z_]+)[ _-]?(\d+(\.\d+)+)", name)
        if match:
            app_name = match.group(1)
            version = match.group(2)

    if app_name:
        app_name = APP_MAP.get(app_name, app_name)

    return app_name, version

# ================= SAVE FILE =================
async def save_file(update, context):
    try:
        msg = update.channel_post or update.message
        if not msg or not msg.document:
            return

        # nếu set admin thì chặn người khác
        if ADMIN_ID and msg.from_user and msg.from_user.id != ADMIN_ID:
            return

        doc = msg.document
        app_name, version = parse_file(doc, msg.caption)

        if not app_name or not version:
            logging.info("Skip file (no parse)")
            return

        cursor.execute("""
            INSERT OR REPLACE INTO ipa_files (app_name, version, file_id)
            VALUES (?, ?, ?)
        """, (app_name, version, doc.file_id))

        conn.commit()
        logging.info(f"Saved: {app_name} {version}")

    except Exception as e:
        logging.error(f"save_file error: {e}")

# ================= GET =================
async def get_app(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("/get app version")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())
    version = context.args[1]

    cursor.execute("""
        SELECT file_id FROM ipa_files
        WHERE app_name=? AND version=?
    """, (app, version))

    row = cursor.fetchone()

    if row:
        await update.message.reply_document(row[0], caption=f"{app} {version}")
    else:
        await update.message.reply_text("Không có file")

# ================= LIST =================
async def list_app(update, context):
    if not context.args:
        await update.message.reply_text("/list app")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())

    cursor.execute("""
        SELECT version FROM ipa_files
        WHERE app_name=?
        ORDER BY created_at DESC
    """, (app,))

    rows = cursor.fetchall()

    if rows:
        text = "\n".join([r[0] for r in rows])
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("Trống")

# ================= LATEST =================
async def latest(update, context):
    if not context.args:
        await update.message.reply_text("/latest app")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())

    cursor.execute("""
        SELECT version, file_id FROM ipa_files
        WHERE app_name=?
        ORDER BY created_at DESC
        LIMIT 1
    """, (app,))

    row = cursor.fetchone()

    if row:
        await update.message.reply_document(
            row[1],
            caption=f"{app} latest {row[0]}"
        )
    else:
        await update.message.reply_text("Không có data")

# ================= SEARCH =================
async def search(update, context):
    if not context.args:
        await update.message.reply_text("/search keyword")
        return

    keyword = context.args[0].lower()

    cursor.execute("""
        SELECT app_name, version
        FROM ipa_files
        WHERE app_name LIKE ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (f"%{keyword}%",))

    rows = cursor.fetchall()

    if rows:
        text = "\n".join([f"{a} - {v}" for a, v in rows])
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("Không thấy")

# ================= INIT =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("get", get_app))
app.add_handler(CommandHandler("list", list_app))
app.add_handler(CommandHandler("latest", latest))
app.add_handler(CommandHandler("search", search))

app.add_handler(MessageHandler(filters.Document.ALL, save_file))

# ================= RUN FIX =================
print("BOT RUNNING...")
app.run_polling(
    drop_pending_updates=True
)
