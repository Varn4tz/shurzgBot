import asyncio
from playwright.async_api import async_playwright
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.ext import JobQueue
from telegram import Update

# === НАСТРОЙКИ ===
TWITCH_URL = "https://www.twitch.tv/shurzg"
TELEGRAM_BOT_TOKEN = "7269296463:AAGbXFouq_LR5MAOhwHvD-d5rSm1ljv-L2M"
TELEGRAM_CHAT_ID = "381376140"

CHECK_INTERVAL_SECONDS = 300   # ✅ по умолчанию 5 минут
BAN_MESSAGE = "В данный момент этот канал недоступен из-за нарушения Правил сообщества или Условий продаж Twitch."

last_status = None  # глобальное хранение статуса

async def check_twitch_ban_and_screenshot():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            print(f"[Twitch] Проверяю {TWITCH_URL}")
            await page.goto(TWITCH_URL, timeout=10000)
            await page.screenshot(path="screenshot.png")
            content = await page.content()
            await browser.close()
            return (BAN_MESSAGE in content)
    except Exception as e:
        print(f"[Ошибка Twitch] {e}")
        return None

async def twitch_monitor(context: ContextTypes.DEFAULT_TYPE):
    global last_status
    print("[Twitch Monitor] Проверка статуса Twitch канала...")
    is_banned = await check_twitch_ban_and_screenshot()

    if is_banned is None:
        print("[Twitch Monitor] Ошибка проверки. Пропуск.")
        return

    if last_status is None:
        last_status = is_banned
        print(f"[Twitch Monitor] Первый запуск. Статус: {'Забанен' if is_banned else 'Разбанен'}")
        return

    # ✅ Уведомить 10 раз если статус изменился с забанен на разбанен
    if last_status and not is_banned:
        for _ in range(10):
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Twitch канал снова доступен!")
        with open("screenshot.png", "rb") as photo:
            await context.bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo)

    last_status = is_banned

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[Telegram] Получена команда /status")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Проверяю статус Twitch канала...")
    is_banned = await check_twitch_ban_and_screenshot()
    if is_banned is None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❗ Не удалось проверить канал.")
    else:
        status = "Забанен ❌" if is_banned else "Разбанен ✅"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Статус Twitch канала: {status}")

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[Telegram] Получена команда /screenshot")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Делаю скриншот Twitch канала...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(TWITCH_URL, timeout=10000)
            await page.screenshot(path="screenshot.png")
            await browser.close()

        with open("screenshot.png", "rb") as photo:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo)
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❗ Ошибка при создании скриншота: {e}")

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHECK_INTERVAL_SECONDS
    print("[Telegram] Получена команда /time")

    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❗ Укажите количество минут. Например: /time 5")
        return

    try:
        minutes = int(context.args[0])
        if minutes < 1:
            raise ValueError
        CHECK_INTERVAL_SECONDS = minutes * 60

        # ✅ Удаляем все старые задачи и запускаем новую
        context.application.job_queue.scheduler.remove_all_jobs()
        context.application.job_queue.run_repeating(twitch_monitor, interval=CHECK_INTERVAL_SECONDS, first=0)

        await context.bot.send_message(chat_id=update.effective_chat.id,
            text=f"✅ Новый интервал проверки установлен: {minutes} минут.")
        print(f"[Twitch Monitor] Интервал проверки установлен: {minutes} минут.")
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id,
            text="❗ Ошибка. Укажите целое число больше 0. Например: /time 5")

def main():
    print("✅ Бот запущен и работает!")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("screenshot", screenshot_command))
    app.add_handler(CommandHandler("time", time_command))

    # ✅ Запуск мониторинга через JobQueue
    app.job_queue.run_repeating(twitch_monitor, interval=CHECK_INTERVAL_SECONDS, first=0)

    print("[Telegram] Бот слушает команды...")
    app.run_polling()

if __name__ == "__main__":
    main()
