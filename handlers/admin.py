from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database.groups import is_enabled, set_enabled
from services.registration import register_message_context

router = Router()


async def is_admin(message: Message) -> bool:
    if message.chat.type not in {"group", "supergroup"}:
        return False
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in {"administrator", "creator"}


@router.message(Command("bil"))
async def bil(message: Message):
    register_message_context(message)
    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("⚠️ Este comando funciona em grupos.")
        return

    enabled = is_enabled(message.chat.id)
    await message.answer(
        "🐾 <b>PIT DIVERSÃO</b>\n\n"
        f"Interação: {'🟢 ATIVADA' if enabled else '🔴 DESATIVADA'}\n\n"
        "A base está pronta para receber os desafios e jogos."
    )


@router.message(Command("interagir"))
async def interagir(message: Message):
    register_message_context(message)
    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("⚠️ Este comando funciona em grupos.")
        return

    if not await is_admin(message):
        await message.answer("🔒 Apenas administradores podem alterar essa configuração.")
        return

    new_state = not is_enabled(message.chat.id)
    set_enabled(message.chat.id, new_state)
    await message.answer(
        "🟢 Interação ativada!" if new_state else "🔴 Interação desativada!"
    )
