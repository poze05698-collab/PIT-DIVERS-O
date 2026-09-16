import random
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.users import upsert
from database.groups import upsert,member,enabled
from database.challenges import active,create,win,cancel
from database.points import add,mine,rank
from services.questions import QUESTIONS
from services.text import norm
from services.permissions import admin
router=Router()
@router.message(Command('adivinha'))
async def adivinha(m):
 if m.chat.type not in {'group','supergroup'}:return await m.answer('🎯 Adivinha funciona em grupos.')
 if not enabled(m.chat.id):return await m.answer('🐾 A interação está desativada.')
 upsert(m.from_user);upsert(m.chat);member(m.chat.id,m.from_user.id);c=active(m.chat.id)
 if c:return await m.answer('⏳ Já existe um desafio ativo. O primeiro a acertar ganha os pontos.')
 q=random.choice(QUESTIONS);cid=create(m.chat.id,q[1],q[2],q[0],q[3]);await m.answer(f'🔮 <b>ADIVINHA #{cid}</b>\n\n🎯 {q[0]}\n❓ {q[1]}\n\n⚡ Primeiro a acertar ganha <b>{q[3]} pontos</b>!')

@router.message(Command('desafio'))
async def desafio(m):
 if m.chat.type not in {'group','supergroup'}:return await m.answer('🎯 O desafio funciona em grupos.')
 if not enabled(m.chat.id):return await m.answer('🐾 A interação está desativada.')
 upsert(m.from_user);upsert(m.chat);member(m.chat.id,m.from_user.id);c=active(m.chat.id)
 if c:return await m.answer(f'🧠 Já existe um desafio ativo!\n\n❓ {c["question"]}\n⭐ Vale {c["points"]} pontos.')
 q=random.choice(QUESTIONS);cid=create(m.chat.id,q[1],q[2],q[0],q[3]);await m.answer(f'🧠 <b>DESAFIO #{cid}</b>\n\n🎯 {q[0]}\n❓ {q[1]}\n\n⚡ Primeiro a acertar ganha <b>{q[3]} pontos</b>!')
@router.message(Command('novo_desafio'))
async def novo(m,bot):
 if not await admin(bot,m.chat.id,m.from_user.id):return await m.answer('⛔ Apenas administradores.')
 parts=(m.text or '').partition(' ')[2].split('|')
 if len(parts)!=3:return await m.answer('Use: /novo_desafio pergunta | resposta | pontos')
 try:pts=max(1,int(parts[2].strip()))
 except:return await m.answer('Pontos inválidos.')
 cancel(m.chat.id);cid=create(m.chat.id,parts[0].strip(),norm(parts[1]),'Personalizado',pts);await m.answer(f'🧠 <b>Desafio #{cid}</b>\n❓ {parts[0].strip()}\n⭐ {pts} pontos')
@router.message(Command('ranking'))
async def ranking(m):
 rows=rank(m.chat.id);
 if not rows:return await m.answer('🏆 Ainda não há pontos nesta semana.')
 s=['🏆 <b>RANKING SEMANAL</b>'];med=['🥇','🥈','🥉']
 for i,r in enumerate(rows,1):s.append(f'{med[i-1] if i<=3 else str(i)+"."} {"@"+r["username"] if r["username"] else r["first_name"]} — <b>{r["points"]} pts</b>')
 await m.answer('\n'.join(s))
@router.message(Command('meuspontos'))
async def pontos(m):await m.answer(f'⭐ Você tem <b>{mine(m.chat.id,m.from_user.id)} pontos</b> nesta semana.')
@router.message()
async def respostas(m):
 if m.chat.type not in {'group','supergroup'} or not m.text or m.text.startswith('/'):return
 c=active(m.chat.id)
 if not c or norm(m.text)!=norm(c['answer']):return
 if not win(c['id'],m.from_user.id):return
 upsert(m.from_user);member(m.chat.id,m.from_user.id);add(m.chat.id,m.from_user.id,c['points']);name='@'+m.from_user.username if m.from_user.username else m.from_user.first_name;await m.answer(f'🎉 <b>ACERTOU!</b>\n👤 {name}\n⚡ +{c["points"]} pontos\n⭐ Total: {mine(m.chat.id,m.from_user.id)}')
