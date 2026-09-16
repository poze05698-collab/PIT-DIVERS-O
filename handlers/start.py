from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.users import upsert
from database.groups import upsert,member,enabled
router=Router()
def ctx(m):
 upsert(m.from_user)
 if m.chat.type in {'group','supergroup'}: upsert(m.chat);member(m.chat.id,m.from_user.id)
@router.message(Command('start'))
async def start(m):
 ctx(m); await m.answer('🐾 <b>PIT DIVERSÃO</b>\nBot de entretenimento para grupos do Telegram.\n\nEm grupo, use /pit para abrir o menu.')
@router.message(Command('pit'))
async def pit(m):
 ctx(m); await m.answer('🐾 <b>PIT DIVERSÃO</b>\n\n🎯 /desafio\n🏆 /ranking\n⭐ /meuspontos\n😂 /piada  🍀 /sorte  💡 /conselho\n🔮 /horoscopo  🎲 /dado  🪙 /caraoucoroa\n✊ /ppp  ➗ /matematica  🔤 /embaralhada\n❓ /verdadeirooufalso  🧩 /forca  🧠 /quiz\n👤 /perfil  ❤️ /seguir  📊 /seguidores\n📝 /feedback  🎁 /giveaway\n⚙️ /admin')
@router.message(Command('bil'))
async def bil(m):
 ctx(m)
 if m.chat.type not in {'group','supergroup'}: return await m.answer('Este comando funciona em grupos.')
 await m.answer(f'🐾 <b>PIT DIVERSÃO</b> — interação {"ATIVADA" if enabled(m.chat.id) else "DESATIVADA"}.')
@router.message(Command('ajuda'))
async def ajuda(m): await pit(m)
