# -*- coding: utf-8 -*-
"""
Fonte de perguntas para o PIT DIVERSÃO.
Usa uma API externa e mantém um pequeno cache em memória.
"""

import json
import random
import urllib.request
import urllib.parse
import html

# API atual
API_URL = "https://www.codesnippets.dev.br/public/api/quizzes/v1/questions"

_TIMEOUT = 15
_CACHE = []
_RECENT_IDS = []


def _request(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 PIT-DIVERSAO",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:
        if response.status != 200:
            raise RuntimeError(
                f"API retornou HTTP {response.status}"
            )

        raw = response.read().decode("utf-8")
        return json.loads(raw)


def _clean(value):
    if value is None:
        return ""

    value = html.unescape(str(value))

    return " ".join(
        value.replace("\n", " ").split()
    ).strip()


def _unwrap(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Formatos possíveis da API
        for key in (
            "questions",
            "data",
            "results",
            "items",
            "records",
        ):
            value = data.get(key)

            if isinstance(value, list):
                return value

            if isinstance(value, dict):
                nested = _unwrap(value)

                if nested:
                    return nested

    return []


def _first(item, *keys):
    for key in keys:
        value = item.get(key)

        if value not in (
            None,
            "",
            [],
        ):
            return value

    return None


def normalize(item):
    """
    Converte o formato da API para o formato usado pelo bot.
    """

    if not isinstance(item, dict):
        return None

    question = _clean(
        _first(
            item,
            "question",
            "questionText",
            "text",
            "enunciado",
            "pergunta",
            "title",
        )
    )

    if not question:
        return None

    # ---------------------------------------------------------
    # ALTERNATIVAS
    # ---------------------------------------------------------

    raw_options = _first(
        item,
        "options",
        "alternatives",
        "alternativas",
        "opcoes",
        "choices",
        "answers",
    )

    options = []
    correct = None

    if isinstance(raw_options, dict):
        raw_options = list(
            raw_options.values()
        )

    if isinstance(raw_options, list):

        for opt in raw_options:

            if isinstance(opt, dict):

                text = _clean(
                    _first(
                        opt,
                        "text",
                        "answer",
                        "answerText",
                        "option",
                        "label",
                        "value",
                        "resposta",
                    )
                )

                correct_flag = _first(
                    opt,
                    "isCorrect",
                    "correct",
                    "is_correct",
                    "correta",
                )

                if correct_flag is True:
                    correct = text

            else:
                text = _clean(opt)

            if text:
                options.append(text)

    # ---------------------------------------------------------
    # RESPOSTA CORRETA
    # ---------------------------------------------------------

    answer = _first(
        item,
        "answer",
        "correct_answer",
        "correctAnswer",
        "correct",
        "resposta",
        "resposta_correta",
        "gabarito",
    )

    # Resposta por índice
    if isinstance(answer, int):

        if 0 <= answer < len(options):
            answer = options[answer]

    elif isinstance(answer, str):

        answer = _clean(answer)

        if answer.isdigit():

            index = int(answer)

            if 0 <= index < len(options):
                answer = options[index]

    answer = _clean(answer)

    if not answer:
        answer = correct

    answer = _clean(answer)

    if not answer:
        return None

    # ---------------------------------------------------------
    # GARANTIR ALTERNATIVAS
    # ---------------------------------------------------------

    options = [
        _clean(option)
        for option in options
        if _clean(option)
    ]

    # Remove duplicadas
    options = list(
        dict.fromkeys(options)
    )

    # Coloca a correta entre as opções
    if answer not in options:
        options.append(answer)

    # Precisamos de pelo menos duas opções
    if len(options) < 2:
        return None

    # No máximo 6 botões
    options = options[:6]

    # Se a resposta acabou ficando fora
    # das primeiras 6, substituímos a última.
    if answer not in options:
        options[-1] = answer

    # ---------------------------------------------------------
    # CATEGORIA
    # ---------------------------------------------------------

    category = _clean(
        _first(
            item,
            "category",
            "categoria",
            "subject",
            "tema",
            "type",
        )
    )

    if not category:
        category = "Conhecimentos gerais"

    # ---------------------------------------------------------
    # ID
    # ---------------------------------------------------------

    uid = _first(
        item,
        "id",
        "question_id",
        "questionId",
        "uuid",
    )

    if not uid:
        uid = question

    return {
        "id": str(uid),
        "category": category,
        "question": question,
        "answer": answer,
        "options": options,
    }


def _load():
    global _CACHE

    data = _request(API_URL)

    raw_questions = _unwrap(data)

    parsed = []

    for item in raw_questions:

        question = normalize(item)

        if question:
            parsed.append(question)

    if parsed:
        _CACHE = parsed

    return _CACHE


def fetch_question():
    """
    Busca uma pergunta nova.
    """

    global _RECENT_IDS

    candidates = []

    # Primeiro tenta usar o cache
    if _CACHE:
        candidates = _CACHE

    # Se não houver cache, consulta a API
    else:
        try:
            candidates = _load()
        except Exception:
            candidates = []

    # API não respondeu
    if not candidates:
        return None

    # Evita repetir imediatamente
    available = [
        question
        for question in candidates
        if question["id"] not in _RECENT_IDS
    ]

    # Se todas já foram usadas,
    # libera novamente.
    if not available:
        _RECENT_IDS.clear()
        available = candidates

    question = random.choice(
        available
    )

    _RECENT_IDS.append(
        question["id"]
    )

    # Mantém somente os últimos 100
    if len(_RECENT_IDS) > 100:
        del _RECENT_IDS[:-100]

    result = dict(question)

    result["options"] = list(
        question["options"]
    )

    random.shuffle(
        result["options"]
    )

    return result


def refresh():
    """
    Força uma nova consulta à API.
    """

    global _CACHE

    _CACHE = []

    return _load()
