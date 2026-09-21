from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from services.backup import create_backup
from services.admin_auth import is_global_admin

router = Router(name="backup")

@router.message(Command("backup"))
async def backup_command(message: Message):
    # O backup contém o banco inteiro de todos os grupos e usuários.
    # Portanto, a operação fica restrita ao administrador global e ao privado.
    if message.chat.type != "private":
        return await message.answer("🔐 Por segurança, use /backup no privado do bot.")
    if not is_global_admin(message.from_user.id):
        return await message.answer("⛔ Apenas o administrador global pode solicitar o backup completo.")

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
