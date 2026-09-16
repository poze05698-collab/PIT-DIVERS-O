import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database.connection import init_db
from handlers.start import router as start_router
from handlers.admin import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado no arquivo .env")

    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(admin_router)

    logging.info("PIT DIVERSÃO iniciado")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
