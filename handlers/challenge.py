import random
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.users import upsert as upsert_user
from database.groups import upsert as upsert_group, member, enabled
from database.challenges import active, create, win, cancel
from database.points import add, mine, rank
from services.questions import choose_question
from services.text import norm
from services.permissions import admin
from services.answer_buttons import build_options, keyboard

router=Router(name="challenge")



async def send_random_now(bot, chat_id):
    g = __import__('database.groups', fromlist=['get']).get(chat_id)
    if not g or not bool(g['enabled']):
        return False, '🐾 A interação está desativada.'
    c = active(chat_id)
    if c:
        return False, '⏳ Já existe um desafio ativo! Responda pelos botões acima.'
    points = max(1, int(g['challenge_points'] or 10))
    chance = max(0, min(100, int(g['image_chance'] or 35)))
    if random.randint(1,100) <= chance:
        from handlers.image_challenge import send_image_challenge
        ok = await send_image_challenge(bot, chat_id, points=points)
        return (True, '') if ok else (False, '❌ Não foi possível gerar o desafio visual agora.')
    category, question, answer, _ = choose_question(chat_id)
    await send_text_challenge(bot, chat_id, category, question, answer, points, '🔥 DESAFIO RELÂMPAGO')
    return True, ''


def mention(user):
    if user.username:
        return '@'+escape(user.username)
    return f'<a href="tg://user?id={user.id}">{escape(user.first_name or "Membro")}</a>'


async def send_text_challenge(bot, chat_id, category, question, answer, points, title="DESAFIO"):
    options=build_options(answer, category, question=question)
    cid=create(chat_id, question, norm(answer), category, points)
    text=(f'🧠 <b>{title} #{cid}</b>\n\n'
          f'🎯 Categoria: <b>{escape(category)}</b>\n'
          f'❓ {escape(question)}\n\n'
          f'👇 <b>Escolha a resposta:</b>\n'
          f'⚡ O primeiro a acertar ganha <b>{points} ponto(s)</b>!')
    await bot.send_message(chat_id, text, reply_markup=keyboard(cid, options))
    return cid


@router.message(Command('adivinha'))
async def adivinha(m):
    if m.chat.type not in {'group','supergroup'}: return await m.answer('🎯 Adivinha funciona em grupos.')
    if not enabled(m.chat.id): return await m.answer('🐾 A interação está desativada.')
    upsert_user(m.from_user); upsert_group(m.chat); member(m.chat.id,m.from_user.id)
    c=active(m.chat.id)
    if c: return await m.answer('⏳ Já existe um desafio ativo. O primeiro a acertar ganha os pontos.')
    q=choose_question(m.chat.id)
    await send_text_challenge(m.bot,m.chat.id,q[0],q[1],q[2],q[3],"ADIVINHA")


@router.message(Command('desafio'))
async def desafio(m):
    if m.chat.type not in {'group','supergroup'}: return await m.answer('🎯 O desafio funciona em grupos.')
    if not enabled(m.chat.id): return await m.answer('🐾 A interação está desativada.')
    upsert_user(m.from_user); upsert_group(m.chat); member(m.chat.id,m.from_user.id)
    c=active(m.chat.id)
    if c: return await m.answer(f'🧠 Já existe um desafio ativo!\n\n❓ {escape(c["question"])}\n⭐ Vale {c["points"]} pontos.')
    q=choose_question(m.chat.id)
    await send_text_challenge(m.bot,m.chat.id,q[0],q[1],q[2],q[3],"DESAFIO")


@router.message(Command('novo_desafio'))
async def novo(m,bot):
    if not await admin(bot,m.chat.id,m.from_user.id): return await m.answer('⛔ Apenas administradores.')
    parts=(m.text or '').partition(' ')[2].split('|')
    if len(parts)!=3: return await m.answer('Use: /novo_desafio pergunta | resposta | pontos')
    try: pts=max(1,int(parts[2].strip()))
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
    options=build_options(c['answer'], c['category'], question=c['question'])
    if index<0 or index>=len(options):
        return await callback.answer('Resposta inválida.')
    selected=options[index]
    if norm(selected)!=norm(c['answer']):
        return await callback.answer('❌ Resposta errada! Tente outra.')

    result=win(cid,callback.from_user.id)
    if not result:
        return await callback.answer('⏱️ Alguém acertou primeiro!')

    upsert_user(callback.from_user); member(chat_id,callback.from_user.id)
    add(chat_id,callback.from_user.id,c['points'])
    total=mine(chat_id,callback.from_user.id)
    name=mention(callback.from_user)
    await callback.answer('🎉 Você acertou primeiro!')
    try:
        await callback.message.delete()
    except Exception:
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except Exception: pass
    await callback.message.answer(
        f'🎉 <b>MANDOU BEM!</b>\n\n'
        f'👑 {name} acertou primeiro!\n'
        f'⭐ +{c["points"]} ponto(s)\n'
        f'🏆 <b>Total na semana: {total} pontos</b>'
    )


@router.message()
async def respostas(m):
    # Respostas digitadas continuam aceitas como alternativa de compatibilidade.
    if m.chat.type not in {'group','supergroup'} or not m.text or m.text.startswith('/'): return
    c=active(m.chat.id)
    if not c or norm(m.text)!=norm(c['answer']): return
    if not win(c['id'],m.from_user.id): return
    upsert_user(m.from_user); member(m.chat.id,m.from_user.id); add(m.chat.id,m.from_user.id,c['points'])
    total=mine(m.chat.id,m.from_user.id); name=mention(m.from_user)
    try: await m.bot.delete_message(m.chat.id,c['id'])
    except Exception: pass
    await m.answer(f'🎉 <b>MANDOU BEM!</b>\n\n👑 {name} acertou primeiro!\n⭐ +{c["points"]} ponto(s)\n🏆 <b>Total na semana: {total} pontos</b>')
