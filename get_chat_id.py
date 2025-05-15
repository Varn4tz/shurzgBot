from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

BOT_TOKEN = '7269296463:AAGbXFouq_LR5MAOhwHvD-d5rSm1ljv-L2M'

async def handle_message(update: Update, context):
    print(f"Ваш chat_id: {update.effective_chat.id}")
    await update.message.reply_text(f"Ваш chat_id: {update.effective_chat.id}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()