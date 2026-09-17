import html
import json
import random
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

from config import BASE

URL = "https://opentdb.com/api.php"
CACHE = Path(BASE) / "assets" / "opentdb_cache.db"


def _db():
    c = sqlite3.connect(CACHE, timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, question TEXT UNIQUE, answer TEXT, options_json TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    return c


def _translate_pt(text):
    """Best-effort free translation. If unavailable, returns original text."""
    text = html.unescape(str(text)).strip()
    try:
        q = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=pt&dt=t&q={q}"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        return "".join(part[0] for part in data[0] if part and part[0]).strip() or text
    except Exception:
        return text


def fetch_one():
    params = urllib.parse.urlencode({"amount": 1, "type": "multiple", "encode": "url3986"})
    try:
        with urllib.request.urlopen(f"{URL}?{params}", timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        if data.get("response_code") != 0 or not data.get("results"):
            return None
        q = data["results"][0]
        question = _translate_pt(urllib.parse.unquote(q["question"]))
        answer = _translate_pt(urllib.parse.unquote(q["correct_answer"]))
        incorrect = [_translate_pt(urllib.parse.unquote(x)) for x in q.get("incorrect_answers", [])]
        options = list(dict.fromkeys([answer] + incorrect))
        random.shuffle(options)
        category = "Open Trivia"
        with _db() as c:
            c.execute("INSERT OR IGNORE INTO questions(category,question,answer,options_json) VALUES(?,?,?,?)", (category, question, answer, json.dumps(options, ensure_ascii=False)))
        return category, question, answer, 10
    except Exception:
        return None


def choose():
    with _db() as c:
        row = c.execute("SELECT category,question,answer,options_json FROM questions ORDER BY RANDOM() LIMIT 1").fetchone()
    if row:
        return row[0], row[1], row[2], 10
    return fetch_one()


def get_options(question):
    with _db() as c:
        row = c.execute("SELECT options_json FROM questions WHERE question=? LIMIT 1", (question,)).fetchone()
    if not row:
        return []
    try:
        return json.loads(row[0])
    except Exception:
        return []
