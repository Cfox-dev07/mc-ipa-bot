import os
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters

TOKEN = os.getenv("TOKEN")

async def start(update, context):
    await update.message.reply_text("Bot Minecraft đang chạy")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, save_file))

app.run_polling()
from telegram.ext import MessageHandler, filters

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

            print("Đã lưu:", version, file_id)

        except:
            print("Caption sai")
