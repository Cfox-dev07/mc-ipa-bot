import os
import sqlite3
import re
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("TOKEN")

# ===== DATABASE =====
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

# ===== APP MAP =====
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

# ===== START =====
async def start(update, context):
    await update.message.reply_text(
        "📦 IPA BOT\n\n"
        "Dùng:\n"
        "/get app version\n"
        "/list app\n"
        "/latest app\n\n"
        "Ví dụ:\n"
        "/get minecraft 1.20.1\n"
        "/get gta_sa 2.10"
    )

# ===== PARSE FILE =====
def parse_file(doc, caption):
    app_name = None
    version = None

    # Ưu tiên caption
    if caption:
        try:
            parts = caption.lower().split()
            if len(parts) >= 2:
                app_name = parts[0]
                version = parts[1]
        except:
            pass

    # Nếu không có caption → đọc tên file
    if not version:
        name = doc.file_name.lower()

        # ví dụ: minecraft 1.26.13.ipa
        match = re.search(r"([a-zA-Z_]+)[ _-]?(\d+(\.\d+)+)", name)

        if match:
            app_name = match.group(1)
            version = match.group(2)

    if app_name:
        app_name = APP_MAP.get(app_name, app_name)

    return app_name, version

# ===== SAVE FILE =====
async def save_file(update, context):
    if update.channel_post:
        doc = update.channel_post.document
        caption = update.channel_post.caption

        app_name, version = parse_file(doc, caption)

        if not app_name or not version:
            print("Không đọc được")
            return

        file_id = doc.file_id

        cursor.execute(
            "INSERT OR REPLACE INTO ipa_files (app_name, version, file_id) VALUES (?, ?, ?)",
            (app_name, version, file_id)
        )
        conn.commit()

        print(f"Đã lưu: {app_name} {version}")

# ===== /get =====
async def get_app(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Dùng: /get app version")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())
    version = context.args[1]

    cursor.execute(
        "SELECT file_id FROM ipa_files WHERE app_name=? AND version=?",
        (app, version)
    )
    result = cursor.fetchone()

    if result:
        await update.message.reply_document(
            document=result[0],
            caption=f"📦 {app}\nVersion: {version}"
        )
    else:
        await update.message.reply_text("Không có version này")

# ===== /list =====
async def list_app(update, context):
    if len(context.args) == 0:
        await update.message.reply_text("Dùng: /list app")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())

    cursor.execute(
        "SELECT version FROM ipa_files WHERE app_name=? ORDER BY version",
        (app,)
    )
    rows = cursor.fetchall()

    if rows:
        text = "\n".join([r[0] for r in rows])
        await update.message.reply_text(f"{app}:\n{text}")
    else:
        await update.message.reply_text("Không có dữ liệu")

# ===== /latest =====
async def latest(update, context):
    if len(context.args) == 0:
        await update.message.reply_text("Dùng: /latest app")
        return

    app = APP_MAP.get(context.args[0].lower(), context.args[0].lower())

    cursor.execute(
        "SELECT version, file_id FROM ipa_files WHERE app_name=? ORDER BY version DESC LIMIT 1",
        (app,)
    )
    result = cursor.fetchone()

    if result:
        await update.message.reply_document(
            document=result[1],
            caption=f"📦 {app}\nLatest: {result[0]}"
        )
    else:
        await update.message.reply_text("Không có dữ liệu")

# ===== INIT =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("get", get_app))
app.add_handler(CommandHandler("list", list_app))
app.add_handler(CommandHandler("latest", latest))
app.add_handler(MessageHandler(filters.Document.ALL, save_file))

print("Bot đang chạy...")
app.run_polling()
