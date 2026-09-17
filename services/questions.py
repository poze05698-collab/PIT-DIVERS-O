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
    """Busca UMA pergunta do banco de perguntas no disco.

    A biblioteca (assets/question_bank.db) e o banco do bot (data/pit_diversao.db)
    sao bancos diferentes. Por isso o historico de perguntas usadas e consultado
    no banco do bot antes de montar a consulta da biblioteca. Isso evita tentar
    acessar a tabela `challenges` dentro de question_bank.db.
    """
    params = []
    where = []

    if category:
        if isinstance(category, (list, tuple, set)):
            cats = list(category)
            if cats:
                where.append("category IN (" + ",".join("?" for _ in cats) + ")")
                params.extend(cats)
        else:
            where.append("category=?")
            params.append(category)

    # Recupera somente as ultimas 50 perguntas usadas no banco principal.
    recent = []
    if group_id is not None:
        try:
            from database.connection import db
            with db() as app_db:
                recent = [
                    row[0]
                    for row in app_db.execute(
                        "SELECT question FROM challenges WHERE group_id=? ORDER BY id DESC LIMIT 50",
                        (group_id,),
                    ).fetchall()
                ]
        except sqlite3.Error:
            # Se o historico ainda nao existir, a inicializacao normal do bot
            # continuara sendo responsavel por criar a tabela.
            recent = []

    def run_query(exclude_recent=True):
        sql = "SELECT category,question,answer,points,options_json FROM questions"
        local_params = list(params)
        conditions = list(where)
        if exclude_recent and recent:
            conditions.append("question NOT IN (" + ",".join("?" for _ in recent) + ")")
            local_params.extend(recent)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY RANDOM() LIMIT 1"
        with _conn() as c:
            return c.execute(sql, tuple(local_params)).fetchone()

    row = run_query(exclude_recent=True)
    if not row:
        # Se todas as perguntas elegiveis estiverem no historico recente,
        # permite repetir uma antiga, mantendo as alternativas originais.
        row = run_query(exclude_recent=False)

    if not row:
        raise RuntimeError("Nenhuma pergunta encontrada na biblioteca")
    return row["category"], row["question"], row["answer"], row["points"]
