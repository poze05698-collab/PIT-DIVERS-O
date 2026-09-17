from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from services.backup import create_backup

router = Router(name="backup")

@router.message(Command("backup"))
async def backup_command(message: Message):
    # Só o próprio administrador do grupo pode solicitar pelo grupo.
    if message.chat.type in {"group", "supergroup"}:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in {"administrator", "creator"}:
            await message.answer("⛔ Apenas administradores podem criar backup.")
            return

    backup = create_backup()
    if not backup:
        await message.answer("⚠️ Não foi possível criar o backup agora.")
        return

    try:
        await message.bot.send_document(
            message.from_user.id,
            FSInputFile(str(backup)),
            caption=(
                "💾 <b>Backup do PIT DIVERSÃO</b>\n"
                "Este arquivo contém o banco de dados atual "
                "(usuários, grupos, pontos, desafios, rankings e demais dados)."
            ),
        )
        await message.answer("✅ Backup criado e enviado para sua conversa privada com o bot.")
    except Exception:
        await message.answer(
            "✅ Backup criado.\n"
            "Abra uma conversa privada com o bot e envie /start antes de usar /backup."
        )
