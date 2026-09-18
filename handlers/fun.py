import random
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from services.games import dice,coin,ppp,parity,scramble,hangman
router=Router()
@router.message(Command('piada'))
async def piada(m):await m.answer(random.choice(['😂 Por que o livro de matemática ficou triste? Porque tinha muitos problemas!','🤣 O que o zero disse para o oito? Belo cinto!','😎 O computador foi ao médico porque estava com vírus.']))
@router.message(Command('sorte'))
async def sorte(m):await m.answer(random.choice(['🍀 Hoje pode ser um ótimo dia para tentar algo novo!','✨ Uma surpresa pode aparecer quando você menos espera.','🔥 Persistência também é sorte.']))
@router.message(Command('conselho'))
async def conselho(m):await m.answer(random.choice(['💡 Um passo de cada vez ainda é progresso.','💡 Proteja seu tempo e valorize quem soma.','💡 Descansar também faz parte do caminho.']))
@router.message(Command('horoscopo'))
async def horo(m):await m.answer(random.choice(['♈ Áries: energia alta; evite impulsos.','♉ Touro: organização ajuda hoje.','♊ Gêmeos: uma conversa pode render uma boa ideia.','♋ Câncer: cuide do seu tempo.','♌ Leão: criatividade em alta.','♍ Virgem: pequenos ajustes fazem diferença.','♎ Libra: busque equilíbrio.','♏ Escorpião: foco nas prioridades.','♐ Sagitário: curiosidade abre portas.','♑ Capricórnio: constância vale mais que pressa.','♒ Aquário: pense diferente.','♓ Peixes: criatividade em alta.']))
@router.message(Command('dado'))
async def dado(m):await m.answer(f'🎲 Você tirou <b>{dice()}</b>.')
@router.message(Command('caraoucoroa'))
async def moeda(m):await m.answer(f'🪙 Deu <b>{coin().upper()}</b>!')
@router.message(Command('ppp'))
async def jogo_ppp(m):await m.answer(f'✊ Você jogou: <b>{ppp()}</b>\n🤖 O bot jogou: <b>{ppp()}</b>')
@router.message(Command('parouimpar'))
async def par(m):n,r=parity();await m.answer(f'🎯 Número: <b>{n}</b> — <b>{r.upper()}</b>')
@router.message(Command('matematica'))
async def mat(m):
    if m.chat.type not in {'group','supergroup'}: return await m.answer('🧮 Matemática funciona em grupos.')
    from database.groups import enabled
    if not enabled(m.chat.id): return await m.answer('🐾 A interação está desativada.')
    from services.questions import choose_question
    from handlers.challenge import send_text_challenge
    q=choose_question(m.chat.id,category='Matemática')
    await send_text_challenge(m.bot,m.chat.id,q[0],q[1],q[2],max(1,int(__import__('database.groups',fromlist=['get']).get(m.chat.id)['challenge_points'] or 10)),'🧮 MATEMÁTICA',q[4])
@router.message(Command('embaralhada'))
async def emb(m):w,s=scramble();await m.answer(f'🔤 <b>PALAVRA EMBARALHADA</b>\n\n<b>{s}</b>\n💡 Começa com {w[0].upper()}')
@router.message(Command('forca'))
async def forca(m):w=hangman();await m.answer(f'🧩 <b>FORCA</b>\n\n<code>{" ".join("_" for _ in w)}</code>\n💡 Dica: palavra ligada ao PIT DIVERSÃO.\n🔎 {len(w)} letras')
@router.message(Command('verdadeirooufalso'))
async def vf(m):
    if m.chat.type not in {'group','supergroup'}: return await m.answer('❓ Verdadeiro ou falso funciona em grupos.')
    from database.groups import enabled,get
    if not enabled(m.chat.id): return await m.answer('🐾 A interação está desativada.')
    from services.questions import choose_question
    from handlers.challenge import send_text_challenge
    q=choose_question(m.chat.id,category='V/F')
    await send_text_challenge(m.bot,m.chat.id,q[0],q[1],q[2],max(1,int(get(m.chat.id)['challenge_points'] or 10)),'✅ VERDADEIRO OU FALSO',q[4])
@router.message(Command('quiz'))
async def quiz(m):
    if m.chat.type not in {'group','supergroup'}: return await m.answer('🧠 Quiz funciona em grupos.')
    from database.groups import enabled,get
    if not enabled(m.chat.id): return await m.answer('🐾 A interação está desativada.')
    from services.questions import choose_question
    from handlers.challenge import send_text_challenge
    q=choose_question(m.chat.id)
    await send_text_challenge(m.bot,m.chat.id,q[0],q[1],q[2],max(1,int(get(m.chat.id)['challenge_points'] or 10)),'🧠 QUIZ',q[4])
