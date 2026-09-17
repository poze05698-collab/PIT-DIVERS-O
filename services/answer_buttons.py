from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.text import norm

def _unique(values):
    out, seen = [], set()
    for value in values:
        value = str(value).strip()
        key = norm(value)
        if value and key not in seen:
            seen.add(key); out.append(value)
    return out

def build_options(answer: str, category: str = '', size: int = 4, question: str = ''):
    """Carrega somente as alternativas da pergunta atual, direto do SQLite."""
    from services.questions import get_options
    options = _unique(get_options(question))
    if not options:
        try:
            from services.opentdb import get_options as get_remote_options
            options = _unique(get_remote_options(question))
        except Exception:
            options = []
    # A resposta correta sempre precisa estar entre as alternativas desta mesma pergunta.
    if norm(answer) not in {norm(x) for x in options}:
        options = [str(answer).strip()] + [x for x in options if norm(x) != norm(answer)]
    target = 2 if norm(category) in {'v/f','verdadeiro ou falso','verdadeiro/falso'} else size
    return options[:target]

def keyboard(cid: int, options):
    rows=[]
    for i in range(0,len(options),2):
        rows.append([InlineKeyboardButton(text=str(o)[:60], callback_data=f'ans:{cid}:{i+j}') for j,o in enumerate(options[i:i+2])])
    return InlineKeyboardMarkup(inline_keyboard=rows)
