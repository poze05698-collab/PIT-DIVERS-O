from html import escape
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.users import upsert,get
from database.social import follow,unfollow,counts,feedback,reaction
from services.permissions import admin
router=Router()
@router.message(Command('perfil'))
async def perfil(m):
 upsert(m.from_user);f,fi=counts(m.from_user.id);u=get(m.from_user.id);n='@'+escape(u['username']) if u['username'] else escape(u['first_name'] or 'Membro');await m.answer(f'👤 <b>PERFIL</b>\n\n{n}\n🆔 <code>{u["id"]}</code>\n❤️ Seguidores: {f}\n➡️ Seguindo: {fi}')
@router.message(Command('quem'))
async def quem(m):
 if not m.reply_to_message or not m.reply_to_message.from_user:return await m.answer('Responda uma mensagem usando /quem.')
 u=m.reply_to_message.from_user;upsert(u);f,fi=counts(u.id);await m.answer(f'👤 <b>{escape(u.first_name or "Membro")}</b>\n🆔 <code>{u.id}</code>\n❤️ {f} seguidores\n➡️ {fi} seguindo')
@router.message(Command('seguir'))
async def seguir(m):
 if not m.reply_to_message or not m.reply_to_message.from_user:return await m.answer('Responda a pessoa usando /seguir.')
 u=m.reply_to_message.from_user;await m.answer('❤️ Agora você segue '+escape(u.first_name or 'Membro') if follow(m.from_user.id,u.id) else 'ℹ️ Você já segue essa pessoa.')
@router.message(Command('parar'))
async def parar(m):
 if not m.reply_to_message or not m.reply_to_message.from_user:return await m.answer('Responda a pessoa usando /parar.')
 u=m.reply_to_message.from_user;await m.answer('💔 Você deixou de seguir '+escape(u.first_name or 'Membro') if unfollow(m.from_user.id,u.id) else 'ℹ️ Você não seguia essa pessoa.')
@router.message(Command('seguidores'))
async def seguidores(m):f,fi=counts(m.from_user.id);await m.answer(f'❤️ Seguidores: <b>{f}</b>\n➡️ Seguindo: <b>{fi}</b>')
@router.message(Command('feedback'))
async def fb(m):
 t=(m.text or '').partition(' ')[2].strip();
 if not t:return await m.answer('Use /feedback sua mensagem')
 feedback(m.chat.id,m.from_user.id,t);await m.answer('📝 Feedback recebido!')
@router.message(Command('reagir'))
async def reagir(m):
 if m.chat.type not in {'group','supergroup'}:return
 kind=(m.text or '').partition(' ')[2].strip() or '❤️';reaction(m.chat.id,m.from_user.id,kind);await m.answer(f'{escape(kind)} Reação registrada!')
@router.message(Command('giveaway'))
async def giveaway(m,bot):
 if m.chat.type not in {'group','supergroup'} or not await admin(bot,m.chat.id,m.from_user.id):return await m.answer('⛔ Apenas admins em grupos.')
 p=(m.text or '').partition(' ')[2].strip()
 if not p:return await m.answer('Use /giveaway prêmio')
 from datetime import datetime,timezone
 from database.connection import db
 with db() as c:
  cur=c.execute('INSERT INTO giveaways(group_id,prize,created) VALUES(?,?,?)',(m.chat.id,p,datetime.now(timezone.utc).isoformat())); gid=cur.lastrowid
 await m.answer(f'🎁 <b>SORTEIO #{gid}</b>\nPrêmio: <b>{escape(p)}</b>\n\nPara participar, use /entrargiveaway #{gid}.\nPara sortear, o admin usa /sortear #{gid}.')
@router.message(Command('entrargiveaway'))
async def enter_giveaway(m):
 import re
 x=(m.text or '').partition(' ')[2].strip(); gid=int(x) if x.isdigit() else 0
 if not gid:return await m.answer('Use /entrargiveaway ID')
 from datetime import datetime,timezone
 from database.connection import db
 with db() as c:
  row=c.execute("SELECT id,group_id,status FROM giveaways WHERE id=?",(gid,)).fetchone()
  if not row or row['group_id']!=m.chat.id or row['status']!='open':return await m.answer('❌ Sorteio não encontrado ou encerrado.')
  try:c.execute('INSERT INTO giveaway_entries VALUES(?,?,?)',(gid,m.from_user.id,datetime.now(timezone.utc).isoformat()))
  except:c.rollback(); return await m.answer('ℹ️ Você já está participando.')
 await m.answer('🎟️ Você entrou no sorteio!')
@router.message(Command('sortear'))
async def draw(m,bot):
 if not await admin(bot,m.chat.id,m.from_user.id):return await m.answer('⛔ Apenas admins.')
 x=(m.text or '').partition(' ')[2].strip(); gid=int(x) if x.isdigit() else 0
 from database.connection import db
 import random
 with db() as c:
  row=c.execute("SELECT * FROM giveaways WHERE id=? AND group_id=? AND status='open'",(gid,m.chat.id)).fetchone()
  if not row:return await m.answer('❌ Sorteio não encontrado ou encerrado.')
  entries=c.execute('SELECT user_id FROM giveaway_entries WHERE giveaway_id=?',(gid,)).fetchall()
  if not entries:return await m.answer('❌ Ainda não há participantes.')
  uid=random.choice(entries)['user_id']; c.execute("UPDATE giveaways SET status='closed',winner=? WHERE id=?",(uid,gid))
 try:u=await bot.get_chat_member(m.chat.id,uid); name=u.user.mention_html()
 except:name=f'<code>{uid}</code>'
 await m.answer(f'🏆 <b>SORTEIO #{gid} ENCERRADO!</b>\n\n🎁 {escape(row["prize"] or "") }\n🥇 Ganhador: {name}')
