# -*- coding: utf-8 -*-
"""Biblioteca de perguntas do PIT DIVERSAO com carregamento sob demanda.

As 15.000 perguntas ficam em SQLite no disco. O bot nunca carrega a
biblioteca inteira para a RAM; cada interacao busca apenas uma pergunta.
"""
import json
import random
import sqlite3
from pathlib import Path
from config import BASE

QUESTION_DB = Path(BASE) / "assets" / "question_bank.db"

# Mantido apenas para compatibilidade com codigo antigo: nao importar a
# biblioteca inteira. Use choose_question()/get_question_options().
QUESTIONS = None

def _conn():
    c = sqlite3.connect(QUESTION_DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA query_only=ON")
    c.execute("PRAGMA busy_timeout=10000")
    return c

def categories():
    with _conn() as c:
        return [r[0] for r in c.execute("SELECT DISTINCT category FROM questions ORDER BY category").fetchall()]

def get_by_question(question):
    with _conn() as c:
        return c.execute("SELECT * FROM questions WHERE question=? LIMIT 1", (question,)).fetchone()

def get_options(question):
    row = get_by_question(question)
    if not row:
        return []
    return json.loads(row["options_json"])

def count(category=None):
    with _conn() as c:
        if category:
            return c.execute("SELECT COUNT(*) FROM questions WHERE category=?", (category,)).fetchone()[0]
        return c.execute("SELECT COUNT(*) FROM questions").fetchone()[0]

def choose_question(group_id=None, category=None):
    """Busca UMA pergunta no disco, evitando as ultimas 50 usadas no grupo."""
    params=[]
    where=[]
    if category:
        if isinstance(category,(list,tuple,set)):
            cats=list(category)
            if cats:
                where.append("category IN (" + ",".join("?" for _ in cats) + ")")
                params.extend(cats)
        else:
            where.append("category=?")
            params.append(category)
    recent_sql = ""
    if group_id is not None:
        recent_sql = " AND question NOT IN (SELECT question FROM challenges WHERE group_id=? ORDER BY id DESC LIMIT 50)"
        params.append(group_id)
    base = "SELECT category,question,answer,points,options_json FROM questions"
    if where:
        base += " WHERE " + " AND ".join(where) + recent_sql
    else:
        base += " WHERE 1=1" + recent_sql
    base += " ORDER BY RANDOM() LIMIT 1"
    with _conn() as c:
        row=c.execute(base,tuple(params)).fetchone()
        if not row:
            # Se todas as perguntas recentes esgotarem, permite repetir a
            # biblioteca inteira, mas nunca cria alternativas novas.
            base2="SELECT category,question,answer,points,options_json FROM questions"
            if where:
                base2 += " WHERE " + " AND ".join(where)
            base2 += " ORDER BY RANDOM() LIMIT 1"
            row=c.execute(base2,tuple(params[:len(params)-(1 if group_id is not None else 0)])).fetchone()
        if not row:
            raise RuntimeError("Nenhuma pergunta encontrada na biblioteca")
        return row["category"], row["question"], row["answer"], row["points"]
