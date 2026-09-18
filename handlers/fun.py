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
 a=random.randint(2,20);b=random.randint(2,20);op=random.choice(['+','-','*']);ans=a+b if op=='+' else a-b if op=='-' else a*b;await m.answer(f'🧮 Quanto é <b>{a} {op} {b}</b>?\nResposta: <b>{ans}</b>')
@router.message(Command('embaralhada'))
async def emb(m):w,s=scramble();await m.answer(f'🔤 <b>PALAVRA EMBARALHADA</b>\n\n<b>{s}</b>\n💡 Começa com {w[0].upper()}')
@router.message(Command('forca'))
async def forca(m):w=hangman();await m.answer(f'🧩 <b>FORCA</b>\n\n<code>{" ".join("_" for _ in w)}</code>\n💡 Dica: palavra ligada ao PIT DIVERSÃO.\n🔎 {len(w)} letras')
@router.message(Command('verdadeirooufalso'))
async def vf(m):s,a=random.choice([('O Brasil fica na América do Sul.','VERDADEIRO'),('O Sol é um planeta.','FALSO'),('Uma semana tem 7 dias.','VERDADEIRO'),('A Lua é maior que o Sol.','FALSO')]);await m.answer(f'❓ {s}\n\nResposta: <b>{a}</b>')
@router.message(Command('quiz'))
async def quiz(m):q=random.choice([('Capital do Brasil?','A) Brasília | B) Roma | C) Lima','A'),('Quantos lados tem um triângulo?','A) 2 | B) 3 | C) 4','B'),('Maior planeta do Sistema Solar?','A) Marte | B) Terra | C) Júpiter','C')]);await m.answer(f'🧠 <b>QUIZ</b>\n\n{q[0]}\n{q[1]}\n\nResposta: <b>{q[2]}</b>')
