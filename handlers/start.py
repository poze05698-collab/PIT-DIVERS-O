from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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


HOWTO_TRIGGERS = {
    "como funciona",
    "como funciona?",
    "como funciona o bot",
    "como participar",
    "como eu participo",
    "o que esse bot faz",
    "como ganhar pontos",
    "quero participar",
}

def _is_howto_text(text: str) -> bool:
    if not text:
        return False
    normalized = " ".join(text.lower().strip().split())
    return normalized in HOWTO_TRIGGERS


# IMPORTANTE: este filtro impede que o handler de texto capture
# /admin e outras mensagens antes dos routers de administração/FSM.
@router.message(F.text.func(_is_howto_text))
async def como_funciona_natural(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not message.text:
        return
    ctx(message)
    from database.features import settings
    s=settings(message.chat.id)
    if not s["howto_enabled"]:
        return
    from html import escape
    member=f'<a href="tg://user?id={message.from_user.id}">{escape(message.from_user.first_name or "Membro")}</a>'
    text=s["howto_text"] or (
        "👋 {member}, veja como funciona o PIT DIVERSÃO! 🐶🔥\n\n"
        "🎯 O bot envia desafios automaticamente.\n"
        "⚡ Quem acertar primeiro ganha pontos.\n"
        "🏆 Os pontos valem para o ranking semanal.\n"
        "🏆 O administrador encerra a temporada pelo painel e publica a premiação do TOP 3.\n\n"
        "🚀 Participe e tente ficar no TOP 3!"
    )
    await message.answer(text.replace("{member}",member))


@router.message(Command("id"))
async def telegram_id(message: Message):
    await message.answer(
        f"🆔 <b>Seu ID do Telegram</b>\n\n<code>{message.from_user.id}</code>\n\n"
        "Use esse número na variável <b>ADMIN_IDS</b> do Discloud para liberar o painel administrativo."
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
