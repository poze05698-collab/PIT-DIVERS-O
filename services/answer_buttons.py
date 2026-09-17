import random
import hashlib
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.text import norm
from services.questions import QUESTIONS


def _unique(values):
    out=[]
    seen=set()
    for value in values:
        value=str(value).strip()
        key=norm(value)
        if value and key not in seen:
            seen.add(key); out.append(value)
    return out


def build_options(answer: str, category: str = "", size: int = 4):
    """Cria alternativas para qualquer desafio textual, mantendo a resposta correta."""
    answer=str(answer).strip()
    pool=[]
    # Respostas existentes são bons distratores para perguntas de conhecimento/charadas.
    for cat, _question, ans, _points in QUESTIONS:
        if category and norm(cat)==norm(category):
            pool.append(ans)
    for _cat, _question, ans, _points in QUESTIONS:
        pool.append(ans)

    # Para respostas numéricas, cria números próximos para não depender do banco.
    try:
        n=int(answer)
        candidates=[n-3,n-2,n-1,n+1,n+2,n+3,n+5,n+10]
        pool.extend(candidates)
    except Exception:
        pass

    options=_unique([answer]+pool)
    # Retira a resposta correta dos candidatos e embaralha.
    correct=answer
    others=[x for x in options if norm(x)!=norm(correct)]
    seed=int(hashlib.sha256(f'{category}|{answer}'.encode('utf-8')).hexdigest()[:16],16)
    rng=random.Random(seed)
    rng.shuffle(others)
    options=[correct]+others[:max(0,size-1)]
    # Se a base não tiver opções suficientes, usa variações simples.
    filler=1
    while len(options)<size:
        candidate=f"Opção {filler}"
        filler+=1
        if norm(candidate) not in {norm(x) for x in options}:
            options.append(candidate)
    rng.shuffle(options)
    return options


def keyboard(cid: int, options):
    rows=[]
    for i in range(0,len(options),2):
        rows.append([
            InlineKeyboardButton(text=str(option)[:60], callback_data=f"ans:{cid}:{i+j}")
            for j, option in enumerate(options[i:i+2])
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
