from html import escape
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.users import upsert
from database.groups import upsert as upsert_group, member, enabled
from database.points import add, mine, rank, season_is_active
from database.features import settings, award, claim_chest_release, unclaim_chest_release, claim_mission, unclaim_mission, category_rank, top3, season_history, spam_ok, victory

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
        '🏆 Os pontos valem para o ranking semanal.\n🏆 O administrador encerra a temporada pelo painel e publica a premiação do TOP 3.\n\n🚀 Participe e tente ficar no TOP 3!')
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
        '🏆 Os pontos valem para o ranking semanal.\n🏆 O administrador encerra a temporada pelo painel e publica a premiação do TOP 3.\n\n🚀 Participe e tente ficar no TOP 3!')
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
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🎁 RESGATAR MISSÃO',callback_data=f'mission:claim:{m.chat.id}')]])
        return await m.answer(f'🎯 <b>MISSÃO CONCLUÍDA!</b>\n\n📊 Progresso: <b>{progress}/{target}</b>\n🎁 Recompensa: <b>{s["mission_reward"]} pontos</b>',reply_markup=kb)
    await m.answer(f'🎯 <b>MISSÃO DIÁRIA</b>\nResponda desafios para avançar.\n📊 Progresso: <b>{progress}/{target}</b>\n🎁 Recompensa: <b>{s["mission_reward"]} pontos</b>')

@router.callback_query(F.data.startswith('mission:claim:'))
async def mission_claim_cb(c):
    try: gid=int(c.data.split(':')[2])
    except Exception: return await c.answer('Missão inválida.')
    if not c.message or c.message.chat.id != gid or c.message.chat.type not in {'group','supergroup'}:
        return await c.answer('Missão inválida.',show_alert=True)
    ensure(type('M',(),{'from_user':c.from_user,'chat':c.message.chat})())
    if not season_is_active(gid):
        return await c.answer('🔒 A temporada foi encerrada. Aguarde o administrador iniciar uma nova.', show_alert=True)
    pts=claim_mission(gid,c.from_user.id)
    if not pts: return await c.answer('Missão já resgatada ou ainda não concluída.',show_alert=True)
    try:
        add(gid,c.from_user.id,pts,reason='Recompensa da missão diária')
    except RuntimeError:
        # Se o Admin encerrar a temporada entre o claim e o crédito,
        # não consumimos a missão: ela poderá ser resgatada na nova temporada.
        unclaim_mission(gid,c.from_user.id)
        return await c.answer('🔒 A temporada foi encerrada antes do crédito. Tente novamente na nova temporada.',show_alert=True)
    await c.answer(f'🎁 +{pts} pontos!')
    try: await c.message.edit_reply_markup(reply_markup=None)
    except Exception: pass
    await c.message.answer(f'🎯 {mention(c.from_user)} resgatou a missão diária e ganhou <b>+{pts} pontos</b>!')

@router.callback_query(F.data.startswith('chest:open:'))
async def chest_button(c):
    try:
        _,_,rid_s,gid_s=c.data.split(':')
        rid=int(rid_s); gid=int(gid_s)
    except Exception:
        return await c.answer('Baú inválido.',show_alert=True)
    if not c.message or c.message.chat.id != gid or c.message.chat.type not in {'group','supergroup'}:
        return await c.answer('Baú inválido.',show_alert=True)
    ensure(type('M',(),{'from_user':c.from_user,'chat':c.message.chat})())
    if not season_is_active(gid):
        return await c.answer('🔒 A temporada foi encerrada. Aguarde o administrador iniciar uma nova.', show_alert=True)
    pts=claim_chest_release(rid,gid,c.from_user.id)
    if not pts:
        return await c.answer('🎁 Você já abriu este baú ou o tempo acabou.',show_alert=True)
    try:
        add(gid,c.from_user.id,pts,reason='Recompensa do baú diário')
    except RuntimeError:
        unclaim_chest_release(rid,gid,c.from_user.id)
        return await c.answer('🔒 A temporada foi encerrada antes do crédito. O baú não foi contabilizado.',show_alert=True)
    await c.answer(f'🎁 Você ganhou +{pts} pontos!')
    await c.message.answer(f'🎁 <b>BAÚ ABERTO!</b>\n\n{mention(c.from_user)} ganhou <b>+{pts} pontos</b>!')

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
