# -*- coding: utf-8 -*-
"""Camada de seleção de perguntas do PIT DIVERSÃO."""
from services.quiz_api import fetch_question

def categories(): return []
def count(category=None): return 0
def get_by_question(question): return None
def get_options(question): return []

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
