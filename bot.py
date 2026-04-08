import asyncio
import logging
import os
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.constants import ParseMode

from content import get_daily_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ALMATY_TZ = pytz.timezone("Asia/Almaty")


async def send_digest(bot: Bot):
    logger.info("Generating daily digest...")
    try:
        message = await get_daily_digest()
        await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        logger.info("Digest sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send digest: {e}")
        await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Ошибка при генерации дайджеста: {e}")


async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID or not ANTHROPIC_API_KEY:
        raise ValueError("Set TELEGRAM_TOKEN, CHAT_ID, ANTHROPIC_API_KEY env vars.")

    bot = Bot(token=TELEGRAM_TOKEN)
    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username}")

    scheduler = AsyncIOScheduler(timezone=ALMATY_TZ)
    # Send every day at 12:00 Almaty time
    scheduler.add_job(send_digest, "cron", hour=12, minute=0, args=[bot])
    scheduler.start()

    logger.info("Scheduler running. Waiting for 12:00 Almaty...")

    # Uncomment to send immediately on startup (for testing):
    # await send_digest(bot)

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
