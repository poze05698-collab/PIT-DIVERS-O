# -*- coding: utf-8 -*-
"""
Fonte externa de perguntas em português para o PIT DIVERSÃO.

A biblioteca local de milhares de perguntas foi removida.
O bot consulta a API sob demanda e mantém somente algumas respostas recentes
em memória para evitar chamadas desnecessárias.
"""
import json
import random
import urllib.parse
import urllib.request
from typing import Any

API_URL = "https://www.codesnippets.dev.br/public/api/quizzes/v1/questions"
_TIMEOUT = 10
_CACHE: list[dict] = []
_RECENT_IDS: list[str] = []


def _request(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PIT-DIVERSAO/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _unwrap(data: Any) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("questions", "data", "results", "items", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = _unwrap(value)
                if nested:
                    return nested
    return []


def _first(item: dict, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return None


def _clean(value) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def normalize(item: dict):
    if not isinstance(item, dict):
        return None

    question = _clean(_first(
        item, "question", "questionText", "text", "enunciado",
        "pergunta", "title"
    ))

    raw_options = _first(
        item, "options", "alternatives", "alternativas",
        "opcoes", "choices", "answers"
    )
    options = []
    correct = None

    if isinstance(raw_options, dict):
        raw_options = list(raw_options.values())

    if isinstance(raw_options, list):
        for opt in raw_options:
            if isinstance(opt, dict):
                text = _clean(_first(
                    opt, "text", "answer", "answerText", "option",
                    "label", "value", "resposta"
                ))
                is_correct = bool(_first(
                    opt, "isCorrect", "correct", "is_correct", "correta"
                ))
                if is_correct:
                    correct = text
            else:
                text = _clean(opt)
            if text:
                options.append(text)

    answer = _clean(_first(
        item, "answer", "correct_answer", "correctAnswer",
        "correct", "resposta", "resposta_correta", "gabarito"
    ))

    # Algumas APIs retornam apenas o índice da alternativa correta.
    if isinstance(answer, int) and 0 <= answer < len(options):
        answer = options[answer]
    elif isinstance(answer, str) and answer.isdigit():
        idx = int(answer)
        if 0 <= idx < len(options):
            answer = options[idx]

    if not answer:
        answer = correct

    if not question or not answer:
        return None

    # Se a API não trouxer alternativas, esta pergunta não serve para
    # o sistema de botões do PIT DIVERSÃO.
    if len(options) < 2:
        return None

    # Garante que a resposta correta esteja entre as alternativas.
    if answer not in options:
        options.append(answer)

    # Remove duplicadas preservando ordem.
    options = list(dict.fromkeys(options))
    if len(options) < 2:
        return None

    category = _clean(_first(
        item, "category", "categoria", "subject", "tema", "type"
    )) or "Conhecimentos gerais"

    uid = str(_first(item, "id", "question_id", "questionId", "uuid") or question)
    return {
        "id": uid,
        "category": category,
        "question": question,
        "answer": answer,
        "options": options[:6],
    }


def _load() -> list[dict]:
    global _CACHE
    data = _request(API_URL)
    raw = _unwrap(data)
    parsed = []
    for item in raw:
        q = normalize(item)
        if q:
            parsed.append(q)
    if parsed:
        _CACHE = parsed
    return _CACHE


def fetch_question() -> dict | None:
    """Busca uma questão em português com alternativas."""
    global _RECENT_IDS

    candidates = _CACHE[:]
    try:
        if not candidates:
            candidates = _load()
    except Exception:
        candidates = _CACHE[:]

    if not candidates:
        return None

    available = [q for q in candidates if q["id"] not in _RECENT_IDS]
    if not available:
        _RECENT_IDS.clear()
        available = candidates

    q = random.choice(available)
    _RECENT_IDS.append(q["id"])
    if len(_RECENT_IDS) > 100:
        del _RECENT_IDS[:-100]

    result = dict(q)
    result["options"] = list(q["options"])
    random.shuffle(result["options"])
    return result


def refresh():
    """Força uma nova leitura da API."""
    global _CACHE
    _CACHE = []
    return _load()
