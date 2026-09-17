from html import escape
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.users import upsert
from database.groups import upsert as upsert_group, member, enabled
from database.points import add, mine, rank
from database.features import settings, award, claim_chest, claim_mission, category_rank, top3, season_history, spam_ok

router=Router(name='features')

def mention(u):
    return f'<a href="tg://user?id={u.id}">{escape(u.first_name or "Membro")}</a>'

def group_only(m): return m.chat.type in {'group','supergroup'}

def ensure(m):
    upsert(m.from_user); upsert_group(m.chat); member(m.chat.id,m.from_user.id)

@router.message(Command('como_funciona'))
async def how_cmd(m):
    if not group_only(m): return await m.answer('🐾 Este comando funciona no grupo.')
    ensure(m); s=settings(m.chat.id)
    if not s['howto_enabled']: return
    text=s['howto_text'] or ('👋 {member}, veja como funciona o PIT DIVERSÃO! 🐶🔥\n\n'
        '🎯 O bot envia desafios automaticamente.\n⚡ Quem acertar primeiro ganha pontos.\n'
        '🏆 Os pontos valem para o ranking semanal.\n🎁 Todo domingo acontece a premiação do TOP 3.\n\n🚀 Participe e tente ficar no TOP 3!')
    await m.answer(text.replace('{member}',mention(m)))

@router.message(F.text.func(lambda text: bool(text) and any(k in text.casefold() for k in (
    'como funciona', 'como participar', 'como ganhar pontos', 'o que esse bot faz',
    'o que o bot faz', 'como eu participo'
))))
async def how_text(m):
    if not group_only(m): return
    ensure(m); s=settings(m.chat.id)
    if not s['howto_enabled']: return
    text=s['howto_text'] or ('👋 {member}, veja como funciona o PIT DIVERSÃO! 🐶🔥\n\n'
        '🎯 O bot envia desafios automaticamente.\n⚡ Quem acertar primeiro ganha pontos.\n'
        '🏆 Os pontos valem para o ranking semanal.\n🎁 Todo domingo acontece a premiação do TOP 3.\n\n🚀 Participe e tente ficar no TOP 3!')
    await m.answer(text.replace('{member}',mention(m.from_user)))


@router.message(Command('nivel'))
async def nivel(m):
    if not group_only(m): return
    ensure(m); s=settings(m.chat.id)
    from database.connection import db
    with db() as c: r=c.execute('SELECT level,xp FROM xp_levels WHERE group_id=? AND user_id=?',(m.chat.id,m.from_user.id)).fetchone()
    if not r: return await m.answer(f'⭐ {mention(m.from_user)} ainda está no nível <b>1</b>.')
    await m.answer(f'⭐ {mention(m.from_user)}\n\n🏅 Nível: <b>{r["level"]}</b>\n✨ XP: <b>{r["xp"]}</b>')

@router.message(Command('combo'))
async def combo(m):
    if not group_only(m): return
    ensure(m)
    from database.connection import db
    with db() as c: r=c.execute('SELECT streak,best FROM combos WHERE group_id=? AND user_id=?',(m.chat.id,m.from_user.id)).fetchone()
    await m.answer(f'🔥 {mention(m.from_user)}\nCombo atual: <b>{r["streak"] if r else 0}</b>\nMelhor combo: <b>{r["best"] if r else 0}</b>')

@router.message(Command('conquistas'))
async def achievements(m):
    if not group_only(m): return
    ensure(m)
    from database.connection import db
    with db() as c: rows=c.execute('SELECT badge FROM achievements WHERE group_id=? AND user_id=? ORDER BY created DESC',(m.chat.id,m.from_user.id)).fetchall()
    await m.answer('🏅 <b>SUAS CONQUISTAS</b>\n\n' + ('\n'.join('🏆 '+r['badge'] for r in rows) if rows else 'Ainda nenhuma. Continue participando!'))

@router.message(Command('missao'))
async def mission(m):
    if not group_only(m): return
    ensure(m); s=settings(m.chat.id)
    from database.features import daily_status
    r,_=daily_status(m.chat.id,m.from_user.id)
    progress=r['progress'] if r else 0; target=r['target'] if r else s['mission_target']
    if r and r['claimed']: return await m.answer('🎯 Missão de hoje já foi resgatada!')
    if progress>=target:
        pts=claim_mission(m.chat.id,m.from_user.id); add(m.chat.id,m.from_user.id,pts or 0)
        return await m.answer(f'🎯 <b>MISSÃO CONCLUÍDA!</b>\n🎁 +{pts} pontos')
    await m.answer(f'🎯 <b>MISSÃO DIÁRIA</b>\nResponda desafios para avançar.\n📊 Progresso: <b>{progress}/{target}</b>')

@router.message(Command('bau'))
async def chest(m):
    if not group_only(m): return
    ensure(m); pts=claim_chest(m.chat.id,m.from_user.id)
    if not pts: return await m.answer('🎁 Seu baú de hoje já foi aberto ou está desativado.')
    add(m.chat.id,m.from_user.id,pts)
    await m.answer(f'🎁 <b>BAÚ DIÁRIO ABERTO!</b>\n\n{mention(m.from_user)} ganhou <b>+{pts} pontos</b>!')

@router.message(Command('rankingcategoria'))
async def category(m):
    if not group_only(m): return
    ensure(m); parts=(m.text or '').split(maxsplit=1); cat=parts[1].strip() if len(parts)>1 else None
    if not cat: return await m.answer('📊 Use: <b>/rankingcategoria Futebol</b>')
    rows=category_rank(m.chat.id,cat)
    if not rows: return await m.answer('📊 Ainda não há pontuação nessa categoria.')
    text=[f'📊 <b>RANKING — {escape(cat)}</b>']
    for i,r in enumerate(rows,1): text.append(f'{i}. {mention(type("U",(),{"id":r["user_id"],"first_name":r["first_name"]})())} — <b>{r["points"]}</b>')
    await m.answer('\n'.join(text))

@router.message(Command('historico'))
async def history(m):
    if not group_only(m): return
    ensure(m); rows=season_history(m.chat.id)
    if not rows: return await m.answer('📚 Ainda não há temporadas encerradas.')
    text=['📚 <b>HISTÓRICO DAS TEMPORADAS</b>']
    for r in rows:
        winners=[r['winner1'],r['winner2'],r['winner3']]; pts=[r['points1'],r['points2'],r['points3']]
        text.append(f'\n📅 {r["week"]}\n🥇 {pts[0]} pts | 🥈 {pts[1]} pts | 🥉 {pts[2]} pts')
    await m.answer('\n'.join(text))

@router.message(Command('top3'))
async def top(m):
    if not group_only(m): return
    ensure(m); rows=top3(m.chat.id)
    if not rows: return await m.answer('🏆 Ainda não há pontos nesta semana.')
    medals=['🥇','🥈','🥉']; text=['🏆 <b>TOP 3 DA SEMANA</b>']
    for i,r in enumerate(rows): text.append(f'{medals[i]} <a href="tg://user?id={r["user_id"]}">{escape(r["first_name"] or "Membro")}</a> — <b>{r["points"]} pts</b>')
    await m.answer('\n'.join(text))

@router.message(Command('batalha'))
async def battle(m):
    if not group_only(m): return
    ensure(m); s=settings(m.chat.id)
    if not s['battles_enabled']: return await m.answer('⚔️ As batalhas estão desativadas.')
    if not m.reply_to_message: return await m.answer('⚔️ Responda à mensagem de um membro com <b>/batalha</b>.')
    opponent=m.reply_to_message.from_user
    if opponent.id==m.from_user.id or opponent.is_bot: return await m.answer('⚔️ Escolha outro membro.')
    from database.connection import db
    with db() as c:
        cur=c.execute('INSERT INTO battles(group_id,challenger,opponent,status,created,points) VALUES(?,?,?,?,?,?)',(m.chat.id,m.from_user.id,opponent.id,'pending',datetime.now(timezone.utc).isoformat(),s['battle_points']))
        bid=cur.lastrowid
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⚔️ Aceitar batalha',callback_data=f'battle:accept:{bid}')]])
    await m.answer(f'⚔️ {mention(m.from_user)} desafiou {mention(opponent)} para uma batalha de <b>{s["battle_points"]} pontos</b>!',reply_markup=kb)

@router.callback_query(F.data.startswith('battle:accept:'))
async def battle_accept(c):
    try: bid=int(c.data.split(':')[2])
    except: return await c.answer('Batalha inválida.')
    from database.connection import db
    with db() as con:
        r=con.execute('SELECT * FROM battles WHERE id=? AND status=?',(bid,'pending')).fetchone()
        if not r: return await c.answer('Essa batalha já terminou.')
        if c.from_user.id!=r['opponent']: return await c.answer('Somente o desafiado pode aceitar.',show_alert=True)
        winner=r['challenger'] if __import__('random').randint(0,1)==0 else r['opponent']
        con.execute('UPDATE battles SET status="finished",winner=? WHERE id=? AND status="pending"',(winner,bid))
    add(r['group_id'],winner,r['points'])
    await c.answer('Batalha realizada!')
    await c.message.answer(f'⚔️ <b>BATALHA FINALIZADA!</b>\n\n🏆 Vencedor: <a href="tg://user?id={winner}">vencedor</a>\n⭐ +{r["points"]} pontos')
