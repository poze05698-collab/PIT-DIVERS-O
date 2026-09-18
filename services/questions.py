# -*- coding: utf-8 -*-
"""Camada de seleção de perguntas do PIT DIVERSÃO."""
from services.quiz_api import fetch_question

def _load_all():
    from services.quiz_api import fetch_question
    # fetch_question already maintains the API/fallback cache.
    return []

def categories():
    from services.quiz_api import _CACHE, _fallback_questions
    source=_CACHE or _fallback_questions()
    return sorted({q['category'] for q in source if q.get('category')})

def count(category=None):
    from services.quiz_api import _CACHE, _fallback_questions
    source=_CACHE or _fallback_questions()
    if category is None: return len(source)
    return sum(1 for q in source if str(q.get('category','')).casefold()==str(category).casefold())

def get_by_question(question):
    from services.quiz_api import _CACHE, _fallback_questions
    source=_CACHE or _fallback_questions()
    for q in source:
        if q.get('question')==question: return q
    return None

def get_options(question):
    q=get_by_question(question)
    return list(q.get('options',[])) if q else []

def choose_question(group_id=None, category=None):
    from database.connection import db
    recent=set()
    if group_id is not None:
        try:
            with db() as c:
                rows=c.execute("SELECT question FROM challenges WHERE group_id=? ORDER BY id DESC LIMIT 30",(group_id,)).fetchall()
                recent={row[0] for row in rows if row[0]}
        except Exception: pass
    for _ in range(6):
        q=fetch_question(category=category)
        if q and q["question"] not in recent:
            return q["category"],q["question"],q["answer"],10,q["options"]
    q=fetch_question(category=category)
    if not q:
        raise RuntimeError("Não foi possível obter uma pergunta no momento.")
    return q["category"],q["question"],q["answer"],10,q["options"]
