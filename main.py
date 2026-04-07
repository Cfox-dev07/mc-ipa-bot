import os
import sqlite3
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("TOKEN")

# ===== DATABASE =====
conn = sqlite3.connect("ipa.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS ipa_files (
    version TEXT PRIMARY KEY,
    file_id TEXT
)
""")
conn.commit()

# ===== START =====
async def start(update, context):
    await update.message.reply_text("🎮 Minecraft IPA Bot đang chạy\nDùng /get version")

# ===== LƯU FILE TỪ CHANNEL =====
async def save_file(update, context):
    if update.channel_post:
        doc = update.channel_post.document
        caption = update.channel_post.caption

        if not caption:
            return

        try:
            app_name, version = caption.split()

            if app_name.lower() != "minecraft":
                return

            file_id = doc.file_id

            cursor.execute(
                "INSERT OR REPLACE INTO ipa_files (version, file_id) VALUES (?, ?)",
                (version, file_id)
            )
            conn.commit()

            print(f"Đã lưu: {version}")

        except:
            print("Caption sai format")

# ===== /get =====
async def get_mc(update, context):
    if len(context.args) == 0:
        await update.message.reply_text("Dùng: /get version")
        return

    version = context.args[0]

    cursor.execute("SELECT file_id FROM ipa_files WHERE version=?", (version,))
    result = cursor.fetchone()

    if result:
        await update.message.reply_document(
            document=result[0],
            caption=f"🎮 Minecraft\nVersion: {version}"
        )
    else:
        await update.message.reply_text("Không có version này")

# ===== /list =====
async def list_ver(update, context):
    cursor.execute("SELECT version FROM ipa_files ORDER BY version")
    rows = cursor.fetchall()

    if rows:
        text = "\n".join([r[0] for r in rows])
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("Chưa có dữ liệu")

# ===== /latest =====
async def latest(update, context):
    cursor.execute("SELECT version, file_id FROM ipa_files ORDER BY version DESC LIMIT 1")
    result = cursor.fetchone()

    if result:
        await update.message.reply_document(
            document=result[1],
            caption=f"🎮 Minecraft\nLatest: {result[0]}"
        )
    else:
        await update.message.reply_text("Chưa có dữ liệu")

# ===== INIT BOT =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("get", get_mc))
app.add_handler(CommandHandler("list", list_ver))
app.add_handler(CommandHandler("latest", latest))
app.add_handler(MessageHandler(filters.Document.ALL, save_file))

print("Bot đang chạy...")
app.run_polling()
