# -*- coding: utf-8 -*-
"""Fonte de perguntas do PIT DIVERSÃO.

A API é a fonte principal. Se a API estiver indisponível ou retornar um
formato inválido, o bot usa um pequeno conjunto de emergência em português
para que os desafios continuem funcionando.
"""
import html
import json
import random
import time
import urllib.parse
import urllib.request

API_URLS = [
    "https://www.codesnippets.dev.br/public/api/quizzes/v1/questions",
    "https://www.codesnippets.dev.br/public/api/quizzes/v1/questions/search?q=Brasil",
    "https://www.codesnippets.dev.br/public/api/quizzes/v1/questions/search?q=futebol",
    "https://www.codesnippets.dev.br/public/api/quizzes/v1/questions/search?q=musica",
]
_TIMEOUT = 2.5
_CACHE = []
_RECENT_IDS = []
_API_RETRY_AFTER = 0.0

# Perguntas de emergência: não substituem a API; evitam que um problema externo
# derrube os botões de Charada, Matemática, V/F e Pergunta.
_FALLBACK = [
    ("Geral", "Qual é a capital do Brasil?", "Brasília", ["Brasília","São Paulo","Rio de Janeiro","Salvador"]),
    ("Geral", "Quantos dias tem uma semana?", "7", ["5","6","7","8"]),
    ("Geral", "Qual planeta é conhecido como Planeta Vermelho?", "Marte", ["Vênus","Marte","Júpiter","Saturno"]),
    ("Geral", "Qual é o maior oceano da Terra?", "Oceano Pacífico", ["Atlântico","Índico","Oceano Pacífico","Ártico"]),
    ("Geral", "Qual é o maior continente?", "Ásia", ["Europa","África","Ásia","Oceania"]),
    ("Futebol", "Quantos jogadores cada time começa em campo no futebol?", "11", ["9","10","11","12"]),
    ("Futebol", "Qual país venceu a Copa do Mundo de 2022?", "Argentina", ["Brasil","França","Argentina","Croácia"]),
    ("Futebol", "Qual é a duração regulamentar de uma partida de futebol?", "90 minutos", ["60 minutos","80 minutos","90 minutos","120 minutos"]),
    ("Futebol", "Qual cartão indica expulsão?", "Vermelho", ["Azul","Amarelo","Verde","Vermelho"]),
    ("Futebol", "Quantos tempos tem uma partida de futebol?", "2", ["1","2","3","4"]),
    ("Filmes e séries", "Qual herói é conhecido como Homem-Aranha?", "Spider-Man", ["Batman","Spider-Man","Superman","Hulk"]),
    ("Filmes e séries", "Qual é o nome do brinquedo cowboy de Toy Story?", "Woody", ["Buzz","Woody","Andy","Rex"]),
    ("Filmes e séries", "Em qual saga aparece o personagem Frodo?", "O Senhor dos Anéis", ["Harry Potter","Star Wars","O Senhor dos Anéis","Matrix"]),
    ("Filmes e séries", "Qual é o nome do ogro verde famoso dos filmes de animação?", "Shrek", ["Shrek","Mike","Simba","Po"]),
    ("Filmes e séries", "Qual é o nome do leão protagonista de O Rei Leão?", "Simba", ["Mufasa","Scar","Simba","Timon"]),
    ("Música", "Quantas cordas tem um violão tradicional?", "6", ["4","5","6","7"]),
    ("Música", "Qual instrumento possui teclas brancas e pretas?", "Piano", ["Violino","Piano","Flauta","Tambor"]),
    ("Música", "Qual é o nome dado a uma música cantada por duas pessoas?", "Dueto", ["Solo","Dueto","Trio","Coral"]),
    ("Música", "Qual aparelho é usado para medir o andamento musical?", "Metrônomo", ["Microfone","Metrônomo","Afinador","Amplificador"]),
    ("Música", "Qual instrumento é tradicionalmente associado ao samba?", "Pandeiro", ["Pandeiro","Harpa","Gaita","Oboé"]),
    ("Brasil", "Qual é a maior floresta tropical do Brasil?", "Amazônia", ["Mata Atlântica","Amazônia","Pantanal","Caatinga"]),
    ("Brasil", "Qual é a capital de Pernambuco?", "Recife", ["Olinda","Recife","Natal","Maceió"]),
    ("Brasil", "Quantos estados o Brasil possui?", "26", ["24","25","26","27"]),
    ("Brasil", "Qual é o maior rio em volume de água do Brasil?", "Rio Amazonas", ["Rio São Francisco","Rio Paraná","Rio Amazonas","Rio Negro"]),
    ("Brasil", "Qual idioma é oficial do Brasil?", "Português", ["Espanhol","Português","Inglês","Francês"]),
    ("Animais e natureza", "Qual é o maior animal terrestre?", "Elefante", ["Girafa","Elefante","Hipopótamo","Rinoceronte"]),
    ("Animais e natureza", "Qual animal é conhecido por mudar de cor para se camuflar?", "Camaleão", ["Cavalo","Camaleão","Pinguim","Golfinho"]),
    ("Animais e natureza", "Qual mamífero é capaz de voar?", "Morcego", ["Morcego","Esquilo","Coala","Lontra"]),
    ("Animais e natureza", "Qual é o maior felino do mundo?", "Tigre", ["Leão","Onça","Tigre","Puma"]),
    ("Animais e natureza", "Qual animal produz mel?", "Abelha", ["Formiga","Abelha","Aranha","Borboleta"]),
    ("Engraçada", "O que pesa mais: 1 kg de ferro ou 1 kg de algodão?", "Pesam o mesmo", ["Ferro","Algodão","Pesam o mesmo","Depende"]),
    ("Engraçada", "Se você jogar uma pedra vermelha no mar azul, o que acontece com ela?", "Fica molhada", ["Fica azul","Fica molhada","Some","Fica leve"]),
    ("Engraçada", "O que tem dentes mas não morde?", "Pente", ["Cachorro","Pente","Peixe","Leão"]),
    ("Engraçada", "O que sobe e desce sem sair do lugar?", "Escada", ["Elevador","Escada","Bola","Nuvem"]),
    ("Engraçada", "O que quanto mais tira, maior fica?", "Buraco", ["Caixa","Buraco","Bola","Copo"]),
    ("Charada", "Tenho folhas, mas não sou árvore. O que sou?", "Livro", ["Livro","Janela","Rio","Sapato"]),
    ("Charada", "Tenho ponteiros, mas não costuro. O que sou?", "Relógio", ["Relógio","Tesoura","Agulha","Régua"]),
    ("Charada", "Quanto mais seca, mais molhada fica. O que é?", "Toalha", ["Chuva","Toalha","Areia","Nuvem"]),
    ("Charada", "Tem pescoço, mas não tem cabeça. O que é?", "Garrafa", ["Garrafa","Camisa","Cobra","Mesa"]),
    ("Charada", "Tem cidades, mas não tem casas; rios, mas não tem água. O que é?", "Mapa", ["Mapa","Livro","Globo","Foto"]),
    ("Matemática", "Quanto é 7 + 8?", "15", ["13","14","15","16"]),
    ("Matemática", "Quanto é 9 x 6?", "54", ["45","48","54","63"]),
    ("Matemática", "Quanto é 100 ÷ 4?", "25", ["20","25","30","40"]),
    ("Matemática", "Quanto é 12²?", "144", ["124","132","144","156"]),
    ("Matemática", "Quanto é 50 - 17?", "33", ["31","32","33","34"]),
    ("V/F", "O Sol é uma estrela.", "Verdadeiro", ["Verdadeiro","Falso"]),
    ("V/F", "A água ferve a 100°C ao nível do mar.", "Verdadeiro", ["Verdadeiro","Falso"]),
    ("V/F", "O Brasil fica na Europa.", "Falso", ["Verdadeiro","Falso"]),
    ("V/F", "A Lua é um satélite natural da Terra.", "Verdadeiro", ["Verdadeiro","Falso"]),
    ("V/F", "Um triângulo possui quatro lados.", "Falso", ["Verdadeiro","Falso"]),
]

def _fallback_questions():
    result=[]
    for i,(cat,q,a,opts) in enumerate(_FALLBACK,1):
        result.append({"id":f"fallback-{i}","category":cat,"question":q,"answer":a,"options":list(opts)})
    return result


def _request(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 PIT-DIVERSAO","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=_TIMEOUT) as response:
        if response.status != 200:
            raise RuntimeError(f"API retornou HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))

def _clean(value):
    if value is None: return ""
    value=html.unescape(str(value))
    return " ".join(value.replace("\n"," ").split()).strip()

def _unwrap(data):
    if isinstance(data,list): return data
    if isinstance(data,dict):
        for key in ("questions","data","results","items","records"):
            value=data.get(key)
            if isinstance(value,list): return value
            if isinstance(value,dict):
                nested=_unwrap(value)
                if nested: return nested
    return []

def _first(item,*keys):
    for key in keys:
        value=item.get(key)
        if value not in (None,"",[]): return value
    return None

def normalize(item):
    if not isinstance(item,dict): return None
    question=_clean(_first(item,"question","questionText","text","enunciado","pergunta","title"))
    if not question: return None
    raw_options=_first(item,"options","alternatives","alternativas","opcoes","choices","answers")
    options=[]; correct=None
    if isinstance(raw_options,dict): raw_options=list(raw_options.values())
    if isinstance(raw_options,list):
        for opt in raw_options:
            if isinstance(opt,dict):
                text=_clean(_first(opt,"text","answer","answerText","option","label","value","resposta"))
                flag=_first(opt,"isCorrect","correct","is_correct","correta")
                if flag is True: correct=text
            else: text=_clean(opt)
            if text: options.append(text)
    answer=_first(item,"answer","correct_answer","correctAnswer","correct","resposta","resposta_correta","gabarito")
    if isinstance(answer,int) and 0<=answer<len(options): answer=options[answer]
    elif isinstance(answer,str):
        answer=_clean(answer)
        if answer.isdigit() and 0<=int(answer)<len(options): answer=options[int(answer)]
    answer=_clean(answer) or _clean(correct)
    if not answer: return None
    options=list(dict.fromkeys(_clean(x) for x in options if _clean(x)))
    if answer not in options: options.append(answer)
    if len(options)<2: return None
    if len(options)>6: options=options[:6]
    if answer not in options: options[-1]=answer
    category=_clean(_first(item,"category","categoria","subject","tema","type")) or "Conhecimentos gerais"
    uid=_first(item,"id","question_id","questionId","uuid") or question
    return {"id":str(uid),"category":category,"question":question,"answer":answer,"options":options}

def _load():
    global _CACHE,_API_RETRY_AFTER
    for url in API_URLS:
        try:
            parsed=[q for item in _unwrap(_request(url)) if (q:=normalize(item))]
            if parsed:
                _CACHE=parsed
                _API_RETRY_AFTER=0
                return _CACHE
        except Exception:
            continue
    _API_RETRY_AFTER=time.time()+300
    _CACHE=_fallback_questions()
    return _CACHE

def _generated_math():
    a=random.randint(2,30); b=random.randint(2,30); op=random.choice(['+','-','*'])
    ans=a+b if op=='+' else a-b if op=='-' else a*b
    options={ans}
    while len(options)<4:
        delta=random.choice([-3,-2,-1,1,2,3])
        options.add(ans+delta)
    opts=list(options); random.shuffle(opts)
    return {"id":f"math-{time.time_ns()}","category":"Matemática","question":f"Quanto é {a} {op} {b}?","answer":str(ans),"options":[str(x) for x in opts]}

def fetch_question(category=None):
    global _RECENT_IDS
    if category and isinstance(category,str) and category.lower() == 'matemática':
        return _generated_math()
    if not _CACHE:
        if time.time() < _API_RETRY_AFTER:
            candidates=_fallback_questions()
        else:
            candidates=_load()
    else:
        candidates=_CACHE
    if category:
        wanted={str(category).lower()} if isinstance(category,str) else {str(x).lower() for x in category}
        filtered=[q for q in candidates if q["category"].lower() in wanted]
        if not filtered:
            aliases={'v/f':{'v/f','verdadeiro ou falso','verdadeiro/falso'},'charada':{'charada'},'matemática':{'matemática','matematica'}}
            expanded=set()
            for w in wanted: expanded |= aliases.get(w,{w})
            filtered=[q for q in candidates if q["category"].lower() in expanded]
        if filtered: candidates=filtered
        elif _CACHE is not candidates:
            candidates=[q for q in _fallback_questions() if q["category"].lower() in wanted] or candidates
    available=[q for q in candidates if q["id"] not in _RECENT_IDS]
    if not available:
        _RECENT_IDS.clear(); available=candidates
    if not available: return None
    q=random.choice(available); _RECENT_IDS.append(q["id"])
    if len(_RECENT_IDS)>100: del _RECENT_IDS[:-100]
    result=dict(q); result["options"]=list(q["options"]); random.shuffle(result["options"]); return result

def refresh():
    global _CACHE,_API_RETRY_AFTER
    _CACHE=[]; _API_RETRY_AFTER=0
