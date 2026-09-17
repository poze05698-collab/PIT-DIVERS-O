from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.users import upsert
from database.groups import upsert as upsert_group, member, enabled, toggle
from services.permissions import admin

router = Router()


def ctx(message: Message):
    upsert(message.from_user)
    if message.chat.type in {"group", "supergroup"}:
        upsert_group(message.chat)
        member(message.chat.id, message.from_user.id)


@router.message(Command("start"))
async def start(message: Message):
    ctx(message)
    await message.answer(
        "🐾 <b>PIT DIVERSÃO</b>\n"
        "Bot de entretenimento para grupos do Telegram.\n\n"
        "👑 Administrador: use <b>/pit</b> para ligar a interação do grupo.\n"
        "📚 Depois, o próprio bot gera desafios automaticamente."
    )


@router.message(Command("pit"))
async def pit(message: Message, bot):
    ctx(message)
    if message.chat.type not in {"group", "supergroup"}:
        return await message.answer(
            "🐾 O comando <b>/pit</b> deve ser usado dentro do grupo."
        )

    if not await admin(bot, message.chat.id, message.from_user.id):
        return await message.answer(
            "⛔ Apenas um administrador do grupo pode usar /pit para ligar o bot."
        )

    toggle(message.chat.id, True)
    await message.answer(
        "🐾 <b>PIT DIVERSÃO ATIVADO!</b>\n\n"
        "🎯 O grupo já está participando.\n"
        "🤖 Os desafios podem ser gerados automaticamente.\n"
        "🖼️ Também serão criados desafios visuais com imagens e botões.\n"
        "🏆 Os pontos ficam registrados durante a semana.\n\n"
        "📌 O painel administrativo fica somente no <b>privado do bot</b>: envie <b>/admin</b>."
    )


@router.message(Command("ajuda"))
async def ajuda(message: Message):
    ctx(message)
    await message.answer(
        "🐾 <b>PIT DIVERSÃO — COMANDOS</b>\n\n"
        "⚡ <b>/pit</b> — ligar a interação no grupo (admin)\n"
        "🧠 <b>/desafio</b> — gerar um desafio agora\n"
        "🖼️ <b>/imagem</b> — gerar um desafio visual agora\n"
        "🏆 <b>/ranking</b> — ranking da semana\n"
        "⭐ <b>/meuspontos</b> — seus pontos\n"
        "😂 <b>/piada</b>  🍀 <b>/sorte</b>  💡 <b>/conselho</b>\n"
        "🔮 <b>/horoscopo</b>  🎲 <b>/dado</b>  🪙 <b>/caraoucoroa</b>\n\n"
        "🤖 O administrador não precisa ficar cadastrando desafios um por um."
    )
