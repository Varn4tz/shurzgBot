import os
import asyncio
from typing import Optional

from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# === НАСТРОЙКИ ИЗ ENV ===
TWITCH_URL = os.getenv("TWITCH_URL", "https://www.twitch.tv/shurzg")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))  # 5 минут по умолчанию
SCREENSHOT_PATH = "/tmp/screenshot.png"

BAN_MESSAGES = [
    "This channel is currently unavailable due to a violation of",
    "В данный момент этот канал недоступен из-за нарушения Правил сообщества или Условий продаж Twitch.",
]

# Глобальное хранение статуса
last_status: Optional[bool] = None


def require_env():
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise RuntimeError(
            "Не заданы переменные окружения: " + ", ".join(missing) +
            ". Добавь их в Railway → Variables."
        )


async def check_twitch_ban_and_screenshot() -> Optional[bool]:
    """
    Возвращает:
      True  -> канал заблокирован/недоступен (по фразам)
      False -> доступен
      None  -> ошибка проверки
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            page = await browser.new_page()
            print(f"[Twitch] Проверяю {TWITCH_URL}")

            await page.goto(TWITCH_URL, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)

            # Скриншот
            await page.screenshot(path=SCREENSHOT_PATH, full_page=True)

            content = await page.content()
            await browser.close()

            return any(msg in content for msg in BAN_MESSAGES)
    except Exception as e:
        print(f"[Ошибка Twitch] {type(e).__name__}: {e}")
        return None


async def twitch_monitor(context: ContextTypes.DEFAULT_TYPE):
    global last_status

    print("[Twitch Monitor] Проверка статуса...")
    is_banned = await check_twitch_ban_and_screenshot()

    if is_banned is None:
        print("[Twitch Monitor] Ошибка проверки. Пропуск.")
        return

    if last_status is None:
        last_status = is_banned
        print(f"[Twitch Monitor] Первый запуск. Статус: {'Забанен' if is_banned else 'Разбанен'}")
        return

    # Уведомляем только при смене статуса "был забанен -> стал доступен"
    if last_status is True and is_banned is False:
        print("[Twitch Monitor] Канал снова доступен! Отправляю уведомления + скриншот.")
        for _ in range(10):
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text="✅ Twitch канал снова доступен!",
            )

        try:
            with open(SCREENSHOT_PATH, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=photo,
                    caption="Скриншот после разбана",
                )
        except Exception as e:
            print(f"[Twitch Monitor] Не смог отправить скриншот: {e}")

    last_status = is_banned


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[Telegram] /status")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⏳ Проверяю статус Twitch канала...",
    )

    is_banned = await check_twitch_ban_and_screenshot()
    if is_banned is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❗ Не удалось проверить канал (ошибка Playwright/сети).",
        )
        return

    status = "Забанен ❌" if is_banned else "Разбанен ✅"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Статус Twitch канала: {status}",
    )


async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[Telegram] /screenshot")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⏳ Делаю скриншот Twitch канала...",
    )

    is_banned = await check_twitch_ban_and_screenshot()
    if is_banned is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❗ Не получилось сделать скриншот (ошибка Playwright/сети).",
        )
        return

    try:
        with open(SCREENSHOT_PATH, "rb") as photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
            )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❗ Ошибка при отправке скриншота: {e}",
        )


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHECK_INTERVAL_SECONDS

    print("[Telegram] /time")
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❗ Укажи количество минут. Например: /time 5",
        )
        return

    try:
        minutes = int(context.args[0])
        if minutes < 1:
            raise ValueError

        CHECK_INTERVAL_SECONDS = minutes * 60

        # Удаляем только нашу задачу по имени и создаём заново
        jq = context.application.job_queue
        for job in jq.jobs():
            if job.name == "twitch_monitor":
                job.schedule_removal()

        jq.run_repeating(
            twitch_monitor,
            interval=CHECK_INTERVAL_SECONDS,
            first=0,
            name="twitch_monitor",
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Новый интервал проверки: {minutes} минут.",
        )
        print(f"[Twitch Monitor] Интервал установлен: {minutes} минут.")
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❗ Ошибка. Укажи целое число > 0. Например: /time 5",
        )


def main():
    require_env()

    print("✅ Бот запускается...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("screenshot", screenshot_command))
    app.add_handler(CommandHandler("time", time_command))

    # Старт фонового мониторинга
    app.job_queue.run_repeating(
        twitch_monitor,
        interval=CHECK_INTERVAL_SECONDS,
        first=0,
        name="twitch_monitor",
    )

    print("[Telegram] Бот слушает команды...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
