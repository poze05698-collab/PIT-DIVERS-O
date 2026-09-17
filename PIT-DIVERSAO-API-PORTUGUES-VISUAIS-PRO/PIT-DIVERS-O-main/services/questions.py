# -*- coding: utf-8 -*-
"""Perguntas do PIT DIVERSÃO obtidas por API, sem biblioteca local."""
from services.quiz_api import fetch_question


def categories():
    # A API pode não oferecer uma lista de categorias separada.
    return []


def count(category=None):
    return 0


def get_by_question(question):
    return None


def get_options(question):
    return []


def choose_question(group_id=None, category=None):
    """
    Busca uma pergunta nova na API.

    O group_id é usado para evitar repetir uma pergunta que apareceu
    recentemente no mesmo grupo. Não existe banco local de milhares de perguntas.
    """
    from database.connection import db

    recent = set()
    if group_id is not None:
        try:
            with db() as c:
                rows = c.execute(
                    "SELECT question FROM challenges WHERE group_id=? "
                    "ORDER BY id DESC LIMIT 30",
                    (group_id,),
                ).fetchall()
                recent = {row[0] for row in rows if row[0]}
        except Exception:
            recent = set()

    # Tenta algumas questões até encontrar uma que não tenha acabado de aparecer.
    for _ in range(5):
        q = fetch_question()
        if not q:
            break
        if q["question"] not in recent:
            return q["category"], q["question"], q["answer"], 10, q["options"]

    # Se a API estiver com poucas questões disponíveis, ainda devolve uma válida.
    q = fetch_question()
    if not q:
        raise RuntimeError("A API de perguntas em português não respondeu.")
    return q["category"], q["question"], q["answer"], 10, q["options"]
