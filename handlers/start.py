from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import BOT_NAME
from services.registration import register_message_context

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    register_message_context(message)

    if message.chat.type in {"group", "supergroup"}:
        await message.answer(
            f"🐾 <b>{BOT_NAME}</b> chegou!\n\n"
            "🎯 Perguntas e desafios\n"
            "🏆 Pontos e ranking semanal\n"
            "🎮 Jogos e brincadeiras\n"
            "🌅 Bom dia e 🌙 boa noite\n\n"
            "A base do sistema está funcionando."
        )
        return

    await message.answer(
        f"🐾 <b>{BOT_NAME}</b>\n\n"
        "Bot de entretenimento para grupos do Telegram.\n\n"
        "Adicione-me a um grupo para começar a interação."
    )
