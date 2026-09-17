import random
import hashlib
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.text import norm
from services.questions import QUESTIONS

# Opções específicas por pergunta. Isso evita misturar respostas de assuntos diferentes.
# A resposta correta SEMPRE é inserida primeiro e depois as alternativas são embaralhadas.
QUESTION_OPTIONS_RAW = {
    'qual é a capital do brasil?': ['Brasília', 'São Paulo', 'Rio de Janeiro', 'Salvador'],
    'quantos dias tem uma semana?': ['7', '5', '6', '8'],
    'qual é o maior estado brasileiro em território?': ['Amazonas', 'Pará', 'Mato Grosso', 'Bahia'],
    'quantos jogadores um time tem em campo no início da partida?': ['11', '10', '9', '12'],
    'qual herói usa um escudo com uma estrela?': ['Capitão América', 'Homem de Ferro', 'Thor', 'Homem-Aranha'],
    'qual instrumento tem normalmente 6 cordas?': ['Violão', 'Guitarra', 'Cavaquinho', 'Ukulele'],
    'quanto é 7 x 8?': ['56', '48', '54', '64'],
    'tem dentes mas não morde. o que é?': ['Pente', 'Garfo', 'Zíper', 'Serrote'],
    'a água ferve a 100 graus celsius ao nível do mar. verdadeiro ou falso?': ['Verdadeiro', 'Falso'],
    'qual é o idioma oficial do brasil?': ['Português', 'Espanhol', 'Inglês', 'Francês'],
    'qual cartão representa expulsão?': ['Vermelho', 'Amarelo', 'Azul', 'Verde'],
    'quanto é 100 dividido por 4?': ['25', '20', '24', '30'],
    'o que sobe e desce sem sair do lugar?': ['Escada', 'Elevador', 'Escada rolante', 'Rampa'],
    'qual planeta é conhecido como planeta vermelho?': ['Marte', 'Júpiter', 'Vênus', 'Saturno'],
}

# Fallbacks por categoria para perguntas novas que ainda não tenham opções próprias.
# Eles mantêm as alternativas dentro do mesmo assunto, em vez de puxar respostas aleatórias.
CATEGORY_POOLS = {
    'filmes e séries': [
        'Capitão América', 'Homem de Ferro', 'Thor', 'Homem-Aranha', 'Hulk',
        'Batman', 'Superman', 'Mulher-Maravilha', 'Flash', 'Aquaman'
    ],
    'futebol': [
        'Gol', 'Pênalti', 'Escanteio', 'Impedimento', 'Falta',
        'Cartão amarelo', 'Cartão vermelho', 'Lateral', 'Cabeçada', 'Drible'
    ],
    'música': [
        'Violão', 'Guitarra', 'Piano', 'Teclado', 'Bateria',
        'Baixo', 'Saxofone', 'Trompete', 'Flauta', 'Violino'
    ],
    'brasil': [
        'Amazonas', 'Pará', 'Bahia', 'São Paulo', 'Minas Gerais',
        'Rio de Janeiro', 'Paraná', 'Goiás', 'Pernambuco', 'Ceará'
    ],
    'charada': [
        'Pente', 'Escada', 'Relógio', 'Sombra', 'Eco',
        'Chave', 'Garfo', 'Espelho', 'Tesoura', 'Livro'
    ],
    'matemática': ['10', '12', '15', '20', '24', '25', '30', '36', '48', '56', '64', '72'],
    'v/f': ['Verdadeiro', 'Falso'],
}


def _unique(values):
    out = []
    seen = set()
    for value in values:
        value = str(value).strip()
        key = norm(value)
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def _question_key(question: str) -> str:
    return norm(str(question).strip())


# As chaves são normalizadas para que acentos e maiúsculas nunca impeçam
# o reconhecimento da pergunta.
QUESTION_OPTIONS = {norm(k): v for k, v in QUESTION_OPTIONS_RAW.items()}


def build_options(answer: str, category: str = '', size: int = 4, question: str = ''):
    """Cria alternativas coerentes com a pergunta.

    Se houver opções cadastradas para a pergunta, elas são usadas diretamente.
    Caso contrário, usa um conjunto da categoria e, para respostas numéricas,
    gera números próximos. Nunca usa respostas de assuntos aleatórios como
    primeira opção de fallback.
    """
    answer = str(answer).strip()
    key = _question_key(question)

    pool = []
    if key in QUESTION_OPTIONS:
        pool.extend(QUESTION_OPTIONS[key])
        # Usa a grafia amigável cadastrada para a resposta correta.
        correct = next((x for x in pool if norm(x) == norm(answer)), answer)
    else:
        correct = answer
        cat_key = norm(category).strip()
        pool.extend(CATEGORY_POOLS.get(cat_key, []))

        # Para perguntas matemáticas/números, cria alternativas numéricas próximas.
        try:
            n = int(answer)
            pool.extend([n - 3, n - 2, n - 1, n + 1, n + 2, n + 3, n + 5, n + 10])
        except Exception:
            pass

        # Último recurso: respostas da mesma categoria no banco.
        if len(_unique(pool)) < size:
            for cat, _q, ans, _points in QUESTIONS:
                if cat_key and norm(cat) == cat_key:
                    pool.append(ans)

    options = _unique([correct] + pool)
    others = [x for x in options if norm(x) != norm(correct)]

    # Ordem determinística: ao validar o clique, os mesmos botões serão reconstruídos.
    seed = int(hashlib.sha256(
        f'{category}|{question}|{answer}'.encode('utf-8')
    ).hexdigest()[:16], 16)
    rng = random.Random(seed)
    rng.shuffle(others)

    options = [correct] + others[:max(0, size - 1)]

    # Se uma pergunta nova não tiver quatro opções, completa com alternativas
    # coerentes sempre que possível. Não usa 'Opção 1', 'Opção 2' etc.
    if len(options) < size:
        cat_key = norm(category).strip()
        extra = CATEGORY_POOLS.get(cat_key, [])
        for candidate in extra:
            if len(options) >= size:
                break
            if norm(candidate) not in {norm(x) for x in options}:
                options.append(candidate)

    # V/F deve ter somente duas respostas; demais desafios tentam ter quatro.
    target = 2 if norm(category).strip() == 'v/f' else size
    options = options[:target]

    rng.shuffle(options)
    return options


def keyboard(cid: int, options):
    rows = []
    for i in range(0, len(options), 2):
        rows.append([
            InlineKeyboardButton(
                text=str(option)[:60],
                callback_data=f'ans:{cid}:{i + j}'
            )
            for j, option in enumerate(options[i:i + 2])
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
