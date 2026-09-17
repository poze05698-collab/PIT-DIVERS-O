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
    """Usa somente alternativas cadastradas junto da pergunta."""
    from services.questions import QUESTIONS
    qkey = norm(question)
    row = next((r for r in QUESTIONS if norm(r[1]) == qkey), None)
    options = _unique(row[4]) if row and len(row) >= 5 else [str(answer).strip()]
    if norm(answer) not in {norm(x) for x in options}:
        options.insert(0, str(answer).strip())
    target = 2 if norm(category) == 'v/f' else size
    return options[:target]

def keyboard(cid: int, options):
    rows=[]
    for i in range(0,len(options),2):
        rows.append([InlineKeyboardButton(text=str(o)[:60], callback_data=f'ans:{cid}:{i+j}') for j,o in enumerate(options[i:i+2])])
    return InlineKeyboardMarkup(inline_keyboard=rows)
