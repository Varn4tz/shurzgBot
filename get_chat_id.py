from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

BOT_TOKEN = "ВАШ_ТОКЕН"

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text(f"Ваш chat_id: {u.effective_chat.id}")))
    app.run_polling()

if __name__ == "__main__":
    main()
