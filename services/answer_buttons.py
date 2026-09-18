from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.text import norm
import json


def _unique(values):
    out, seen = [], set()
    for value in values:
        value = str(value).strip()
        key = norm(value)
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def build_options(answer: str, category: str = '', size: int = 4,
                  question: str = '', supplied=None):
    """
    Usa as alternativas que vieram junto da pergunta da API.
    Elas são salvas no desafio para que o callback reconstrua exatamente
    o mesmo conjunto, inclusive depois de um restart.
    """
    options = _unique(supplied or [])

    if not options and question:
        try:
            from database.connection import db
            with db() as c:
                row = c.execute(
                    "SELECT options_json FROM challenges "
                    "WHERE question=? ORDER BY id DESC LIMIT 1",
                    (question,),
                ).fetchone()
            if row and row["options_json"]:
                options = _unique(json.loads(row["options_json"]))
        except Exception:
            options = []

    if norm(answer) not in {norm(x) for x in options}:
        options = [str(answer).strip()] + [
            x for x in options if norm(x) != norm(answer)
        ]

    target = 2 if norm(category) in {
        'v/f', 'verdadeiro ou falso', 'verdadeiro/falso'
    } else size
    return options[:target]


def keyboard(cid: int, options):
    rows = []
    for i in range(0, len(options), 2):
        rows.append([
            InlineKeyboardButton(
                text=str(o)[:60],
                callback_data=f'ans:{cid}:{i+j}'
            )
            for j, o in enumerate(options[i:i+2])
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
