import asyncio
import random
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.users import upsert as upsert_user
from database.groups import upsert as upsert_group, member, enabled
from database.challenges import active, create, win, cancel, cancel_id
from database.points import add, mine, rank, season_is_active
from database.features import award, victory, spam_ok, reset_combo
from services.questions import choose_question
from services.text import norm
from services.permissions import admin
from services.answer_buttons import build_options, keyboard

router=Router(name="challenge")



async def send_random_now(bot, chat_id):
    g = __import__('database.groups', fromlist=['get']).get(chat_id)
    if not g or not bool(g['enabled']):
        return False, '🐾 A interação está desativada.'
    if not season_is_active(chat_id):
        return False, '🔒 A temporada está encerrada.'
    c = active(chat_id)
    if c:
        return False, '⏳ Já existe um desafio ativo! Responda pelos botões acima.'
    points = 10
    chance = max(0, min(100, int(g['image_chance'] or 35)))
    if random.randint(1,100) <= chance:
        from handlers.image_challenge import send_image_challenge
        ok = await send_image_challenge(bot, chat_id, points=points)
        return (True, '') if ok else (False, '❌ Não foi possível gerar o desafio visual agora.')
    category, question, answer, _, options = await asyncio.to_thread(choose_question, chat_id)
    await send_text_challenge(bot, chat_id, category, question, answer, points, '🔥 DESAFIO RELÂMPAGO', options)
    return True, ''


def mention(user):
    if user.username:
        return '@'+escape(user.username)
    return f'<a href="tg://user?id={user.id}">{escape(user.first_name or "Membro")}</a>'


async def send_text_challenge(bot, chat_id, category, question, answer, points, title="DESAFIO", options=None):
    # Nenhum desafio novo pode ser criado enquanto a temporada estiver fechada.
    if not season_is_active(chat_id):
        raise RuntimeError("A temporada está encerrada.")
    # Regra fixa: todo desafio vale exatamente 10 pontos.
    # Mantemos o argumento `points` por compatibilidade com versões antigas.
    points = 10
    options=build_options(answer, category, question=question, supplied=options)
    import json
    cid=create(chat_id, question, norm(answer), category, points, options_json=json.dumps(options, ensure_ascii=False))
    text=(f'🧠 <b>{title} #{cid}</b>\n\n'
          f'🎯 Categoria: <b>{escape(category)}</b>\n'
          f'❓ {escape(question)}\n\n'
          f'👇 <b>Escolha a resposta:</b>\n'
          f'⚡ O primeiro a acertar ganha <b>{points} ponto(s)</b>!')
    try:
        sent=await bot.send_message(chat_id,text,reply_markup=keyboard(cid,options))
    except Exception:
        # Nunca deixar um desafio invisível preso como `active`.
        cancel_id(cid)
        raise
    from database.challenges import set_message_id
    set_message_id(cid,sent.message_id)
    return cid


@router.message(Command('adivinha'))
async def adivinha(m):
    if m.chat.type not in {'group','supergroup'}: return await m.answer('🎯 Adivinha funciona em grupos.')
    if not enabled(m.chat.id): return await m.answer('🐾 A interação está desativada.')
    if not season_is_active(m.chat.id): return await m.answer('🔒 A temporada foi encerrada. O administrador precisa iniciar uma nova temporada.')
    upsert_user(m.from_user); upsert_group(m.chat); member(m.chat.id,m.from_user.id)
    c=active(m.chat.id)
    if c: return await m.answer('⏳ Já existe um desafio ativo. O primeiro a acertar ganha os pontos.')
    q=await asyncio.to_thread(choose_question, m.chat.id)
    await send_text_challenge(m.bot,m.chat.id,q[0],q[1],q[2],q[3],"ADIVINHA",q[4])


@router.message(Command('desafio'))
async def desafio(m):
    if m.chat.type not in {'group','supergroup'}: return await m.answer('🎯 O desafio funciona em grupos.')
    if not enabled(m.chat.id): return await m.answer('🐾 A interação está desativada.')
    if not season_is_active(m.chat.id): return await m.answer('🔒 A temporada foi encerrada. O administrador precisa iniciar uma nova temporada.')
    upsert_user(m.from_user); upsert_group(m.chat); member(m.chat.id,m.from_user.id)
    c=active(m.chat.id)
    if c: return await m.answer(f'🧠 Já existe um desafio ativo!\n\n❓ {escape(c["question"])}\n⭐ Vale {c["points"]} pontos.')
    q=await asyncio.to_thread(choose_question, m.chat.id)
    await send_text_challenge(m.bot,m.chat.id,q[0],q[1],q[2],q[3],"DESAFIO",q[4])


@router.message(Command('novo_desafio'))
async def novo(m,bot):
    if not await admin(bot,m.chat.id,m.from_user.id): return await m.answer('⛔ Apenas administradores.')
    if not season_is_active(m.chat.id): return await m.answer('🔒 A temporada está encerrada. Inicie uma nova temporada pelo painel Admin.')
    parts=(m.text or '').partition(' ')[2].split('|')
    if len(parts)!=3: return await m.answer('Use: /novo_desafio pergunta | resposta | pontos')
    try: pts=10
    except: return await m.answer('Pontos inválidos.')
    cancel(m.chat.id)
    await send_text_challenge(m.bot,m.chat.id,'Personalizado',parts[0].strip(),parts[1].strip(),pts,"DESAFIO PERSONALIZADO")


@router.message(Command('ranking'))
async def ranking(m):
    rows=rank(m.chat.id)
    if not rows: return await m.answer('🏆 Ainda não há pontos nesta semana.')
    s=['🏆 <b>RANKING SEMANAL</b>']; med=['🥇','🥈','🥉']
    for i,r in enumerate(rows,1):
        name='@'+escape(r['username']) if r['username'] else escape(r['first_name'] or 'Membro')
        s.append(f'{med[i-1] if i<=3 else str(i)+"."} {name} — <b>{r["points"]} pts</b>')
    await m.answer('\n'.join(s))


@router.message(Command('meuspontos'))
async def pontos(m):
    await m.answer(f'⭐ Você tem <b>{mine(m.chat.id,m.from_user.id)} pontos</b> nesta semana.')


@router.callback_query(F.data.startswith('ans:'))
async def answer_button(callback: CallbackQuery):
    try:
        _,cid_s,index_s=callback.data.split(':')
        cid=int(cid_s); index=int(index_s)
    except (ValueError,AttributeError):
        return await callback.answer('Desafio inválido.')
    if not callback.message:
        return await callback.answer('Mensagem do desafio não encontrada.')
    chat_id=callback.message.chat.id
    c=active(chat_id)
    if not c or c['id']!=cid:
        return await callback.answer('⏱️ Este desafio já terminou.')

    # Reconstrói exatamente as mesmas alternativas determinísticas do desafio.
    import json
    try: stored_options=json.loads(c['options_json'] or '[]')
    except Exception: stored_options=[]
    options=build_options(c['answer'], c['category'], question=c['question'], supplied=stored_options or None)
    if index<0 or index>=len(options):
        return await callback.answer('Resposta inválida.')
    selected=options[index]
    if norm(selected)!=norm(c['answer']):
        reset_combo(chat_id, callback.from_user.id)
        return await callback.answer('❌ Resposta errada! Tente outra.')
    if not spam_ok(chat_id, callback.from_user.id):
        return await callback.answer('⏳ Você está respondendo rápido demais. Aguarde um pouco.')
    if not season_is_active(chat_id):
        return await callback.answer('🔒 A temporada foi encerrada. Aguarde o administrador iniciar uma nova.', show_alert=True)

    result=win(cid,callback.from_user.id)
    if not result:
        return await callback.answer('⏱️ Alguém acertou primeiro!')

    upsert_user(callback.from_user); member(chat_id,callback.from_user.id)
    add(chat_id,callback.from_user.id,c['points'],reason=f'Desafio {c["category"]}')
    fx=award(chat_id,callback.from_user.id,c['points'],c['category'])
    total=mine(chat_id,callback.from_user.id)
    name=mention(callback.from_user)
    await callback.answer('🎉 Você acertou primeiro!')
    try:
        await callback.message.delete()
    except Exception:
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except Exception: pass
    await callback.message.answer(
        f'{victory(chat_id)}\n\n'
        f'👑 {name} acertou primeiro!\n'
        f'⭐ +{c["points"]} ponto(s)\n'
        f'📊 <b>Total acumulado na temporada: {total} pontos</b>' + (f'\n🔥 Combo: <b>{fx["combo"]}</b>' if fx['combo'] else '') + (f'\n🏅 Nova conquista: <b>{fx["new_badges"][0]}</b>' if fx['new_badges'] else '')
    )


@router.message()
async def respostas(m):
    # Desafios oficiais usam os botões. Respostas digitadas são ignoradas
    # para evitar que uma mensagem comum interfira no desafio.
    return
