import random
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.groups import enabled, get as get_group
from database.users import upsert
from database.features import settings, spam_ok, award, victory
from database.points import add, mine
from database.connection import db
from datetime import datetime, timezone

router=Router(name='memory')
EMOJIS=['🍎','🍋','🍇','🍉','🥝','🍒','🥥','🍓','🍍']

def make_game(gid):
    vals=random.sample(EMOJIS,9); answer=random.randint(1,9); shown=' '.join(vals)
    with db() as c:
        cur=c.execute('INSERT INTO memory_games(group_id,question,answer,status,created) VALUES(?,?,?,?,?)',(gid,'Qual era o símbolo na posição '+str(answer)+'?',vals[answer-1],'active',datetime.now(timezone.utc).isoformat()))
        return cur.lastrowid,shown,answer

def kb(gid):
    rows=[]
    for i in range(1,10,3): rows.append([InlineKeyboardButton(text=str(x),callback_data=f'memory:{gid}:{x}') for x in range(i,i+3)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.message(Command('memoria'))
async def memoria(m):
    if m.chat.type not in {'group','supergroup'}: return await m.answer('🧠 Este jogo funciona em grupos.')
    if not enabled(m.chat.id) or not settings(m.chat.id)['memory_enabled']: return await m.answer('🧠 A memória visual está desativada.')
    upsert(m.from_user)
    with db() as c:
        c.execute('UPDATE memory_games SET status="cancelled" WHERE group_id=? AND status="active"',(m.chat.id,))
    gid,shown,pos=make_game(m.chat.id)
    await m.answer(f'🧠 <b>MEMÓRIA VISUAL</b>\n\n{shown}\n\n👀 Memorize! A sequência será ocultada.\n\nQual símbolo estava na posição <b>{pos}</b>?',reply_markup=kb(gid))

@router.callback_query(F.data.startswith('memory:'))
async def memory_answer(c):
    try: _,gid_s,pos_s=c.data.split(':'); gid=int(gid_s); pos=int(pos_s)
    except: return await c.answer('Jogo inválido.')
    if not spam_ok(gid,c.from_user.id): return await c.answer('⏳ Aguarde um pouco.')
    with db() as con:
        r=con.execute('SELECT * FROM memory_games WHERE id=(SELECT MAX(id) FROM memory_games WHERE group_id=?) AND status="active"',(gid,)).fetchone()
        if not r: return await c.answer('⏱️ Jogo encerrado.')
        # answer stores symbol; question contains correct position
        correct=int(r['question'].rsplit(' ',1)[-1].rstrip('?'))
        if pos!=correct: return await c.answer('❌ Não foi essa posição!')
        con.execute('UPDATE memory_games SET status="answered",winner=? WHERE id=? AND status="active"',(c.from_user.id,r['id']))
    group=get_group(gid)
    pts=max(1,int(group['challenge_points'] if group else 10))
    add(gid,c.from_user.id,pts); fx=award(gid,c.from_user.id,pts,'Memória')
    if fx['bonus']: add(gid,c.from_user.id,fx['bonus'])
    await c.answer('🎉 Você acertou!')
    try: await c.message.edit_reply_markup(reply_markup=None)
    except: pass
    await c.message.answer(f'{victory(gid)}\n👑 <a href="tg://user?id={c.from_user.id}">{c.from_user.first_name or "Membro"}</a> ganhou <b>+{pts+fx["bonus"]} pontos</b>!')
