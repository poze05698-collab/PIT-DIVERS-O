import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, BACKUP_INTERVAL
from database.connection import init_db
from services.backup import restore_if_needed, create_backup
from handlers import backup, start, admin, challenge, image_challenge, fun, social
from services.commands import setup_commands
from services.scheduler import scheduler_loop

# Log enxuto para o Discloud: mostra somente o essencial do bot.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | PIT-DIVERSAO | %(message)s",
    force=True,
)

# O aiogram gera uma linha de log para praticamente cada update.
# Deixamos esses logs detalhados somente quando houver aviso/erro.
for _logger_name in (
    "aiogram",
    "aiogram.event",
    "aiogram.dispatcher",
    "aiogram.middlewares",
    "aiogram.fsm",
    "aiohttp",
):
    logging.getLogger(_logger_name).setLevel(logging.WARNING)

log = logging.getLogger("pit")

async def backup_loop():
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        try:
            create_backup()
        except Exception:
            log.exception("Falha no backup automático")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado")

    # Se o banco estiver ausente/corrompido, tenta recuperar o último backup.
    restore_if_needed()
    init_db()
    create_backup()

    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(challenge.router)
    dp.include_router(image_challenge.router)
    dp.include_router(fun.router)
    dp.include_router(social.router)
    dp.include_router(backup.router)

    await setup_commands(bot)

    scheduler_task = asyncio.create_task(scheduler_loop(bot))
    backup_task = asyncio.create_task(backup_loop())

    log.info("Bot iniciado e pronto para receber mensagens")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        backup_task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
