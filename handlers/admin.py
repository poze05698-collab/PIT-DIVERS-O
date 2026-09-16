from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.groups import toggle,get,setting,prize
from database.challenges import cancel
from services.permissions import admin
router=Router()
@router.message(Command('admin'))
async def panel(m:Message,bot):
 if m.chat.type not in {'group','supergroup'} or not await admin(bot,m.chat.id,m.from_user.id): return await m.answer('⛔ Apenas administradores no grupo.')
 g=get(m.chat.id); await m.answer(f'🛠 <b>PAINEL</b>\nInteração: {"ATIVA" if g["enabled"] else "DESATIVADA"}\nBom dia: {"ATIVO" if g["morning"] else "OFF"}\nBoa noite: {"ATIVO" if g["night"] else "OFF"}\n🎁 Prêmio: {g["prize"] or "não configurado"}\n\n/interagir\n/bomdia_on /bomdia_off\n/boanoite_on /boanoite_off\n/premio texto\n/fecharsemana\n/limpardesafio')
@router.message(Command('interagir'))
async def interagir(m,bot):
 if not await admin(bot,m.chat.id,m.from_user.id): return await m.answer('⛔ Apenas administradores.')
 g=get(m.chat.id);v=not bool(g['enabled']);toggle(m.chat.id,v);await m.answer(f'🐾 Interação {"ATIVADA" if v else "DESATIVADA"}.')
@router.message(Command('bomdia_on','bomdia_off'))
async def bom(m):
 from database.groups import setting; setting(m.chat.id,'morning',m.text.endswith('_on')); await m.answer('🌅 Configuração atualizada.')
@router.message(Command('boanoite_on','boanoite_off'))
async def boa(m):
 setting(m.chat.id,'night',m.text.endswith('_on')); await m.answer('🌙 Configuração atualizada.')
@router.message(Command('premio'))
async def premio(m,bot):
 if not await admin(bot,m.chat.id,m.from_user.id): return await m.answer('⛔ Apenas administradores.')
 t=(m.text or '').split(' ',1);
 if len(t)==1:return await m.answer(f'🎁 Prêmio: {get(m.chat.id)["prize"] or "não configurado"}\nUse /premio texto do prêmio')
 prize(m.chat.id,t[1].strip());await m.answer('🎁 Prêmio semanal salvo.')
@router.message(Command('limpardesafio'))
async def limpar(m,bot):
 if await admin(bot,m.chat.id,m.from_user.id):cancel(m.chat.id);await m.answer('🧹 Desafio encerrado.')
@router.message(Command('anunciar'))
async def anunciar(m,bot):
 if not await admin(bot,m.chat.id,m.from_user.id):return await m.answer('⛔ Apenas administradores.')
 t=(m.text or '').partition(' ')[2].strip();await m.answer('📢 <b>ANÚNCIO</b>\n\n'+(t or 'Use /anunciar mensagem'))
@router.message(Command('fecharsemana'))
async def fechar(m,bot):
 if not await admin(bot,m.chat.id,m.from_user.id):return await m.answer('⛔ Apenas administradores.')
 from database.points import previous_week,close_week
 r=close_week(m.chat.id,previous_week(),get(m.chat.id)['prize'] or 'Prêmio não configurado');await m.answer('🏆 Semana fechada.' if r else 'ℹ️ Não há pontuação ou a semana já foi fechada.')
