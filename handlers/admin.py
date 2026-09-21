import asyncio
import random
from html import escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.groups import get, all_groups, toggle, setting, prize
from database.challenges import cancel
from database.points import previous_week, close_week, close_season, start_new_season, users_with_points, find_group_user, add, mine, points_ledger, active_week, season_status
from services.admin_auth import is_global_admin

router = Router()


# ============================================================
# EDITAR MENSAGEM COM SEGURANÇA
# ============================================================

async def safe_edit(c: CallbackQuery, text: str, reply_markup=None):
    """
    Edita a mensagem do callback sem entrar em recursão.
    Também ignora o erro 'message is not modified'.
    """
    try:
        await c.message.edit_text(
            text,
            reply_markup=reply_markup
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise


# ============================================================
# HORÁRIO
# ============================================================

def parse_time(value):
    """
    Aceita:
    10:00
    10.00
    10:30
    10.30
    0:00
    0.00
    """
    value = (value or "").strip().replace(".", ":")

    parts = value.split(":")

    if len(parts) != 2:
        return None

    try:
        h = int(parts[0].strip())
        mi = int(parts[1].strip())
    except (TypeError, ValueError):
        return None

    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None

    return f"{h:02d}:{mi:02d}"


# ============================================================
# ESTADOS
# ============================================================

class ConfigState(StatesGroup):
    waiting = State()
    kind = State()
    group_id = State()


# ============================================================
# PAINEL PRINCIPAL
# ============================================================

def home_kb():
    b = InlineKeyboardBuilder()

    b.button(
        text="👥 Grupos",
        callback_data="adm:groups"
    )

    b.button(
        text="⚙️ Configurar grupo",
        callback_data="adm:choose"
    )

    b.button(
        text="🎮 Interagir agora",
        callback_data="adm:interact"
    )

    b.button(
        text="🎁 Prêmios",
        callback_data="adm:prizes"
    )

    b.button(
        text="📊 Status geral",
        callback_data="adm:status"
    )

    b.button(
        text="👥 Usuários / Pontos",
        callback_data="adm:users"
    )

    b.button(
        text="⚙️ Sistemas",
        callback_data="adm:systems"
    )

    b.adjust(2)

    return b.as_markup()


# ============================================================
# LISTA DE GRUPOS
# ============================================================

def group_kb(back="adm:home"):
    b = InlineKeyboardBuilder()
    gs = all_groups()

    for g in gs:
        b.button(
            text=f"🐾 {(g['title'] or 'Grupo')[:30]}",
            callback_data=f"adm:g:{g['id']}"
        )

    b.button(
        text="⬅️ Voltar",
        callback_data=back
    )

    b.adjust(1)

    return b.as_markup()


# ============================================================
# CONFIGURAÇÕES DO GRUPO
# ============================================================

def settings_kb(gid):
    g = get(gid)
    b = InlineKeyboardBuilder()

    if not g:
        return group_kb("adm:choose")

    b.button(
        text=(
            "🔴 Desligar interação"
            if g["enabled"]
            else "🟢 Ligar interação"
        ),
        callback_data=f"adm:toggle:{gid}"
    )

    b.button(
        text="⏰ Horário da interação",
        callback_data=f"adm:hours:{gid}"
    )

    b.button(
        text="🔁 Intervalo dos desafios",
        callback_data=f"adm:interval:{gid}"
    )

    b.button(
        text="⭐ Pontos por desafio",
        callback_data=f"adm:points:{gid}"
    )

    b.button(
        text="🖼️ Chance de desafio visual",
        callback_data=f"adm:image:{gid}"
    )

    b.button(
        text=(
            "🔴 Desligar bom dia"
            if g["morning"]
            else "🌅 Ligar bom dia"
        ),
        callback_data=f"adm:morning:{gid}"
    )

    b.button(
        text="🕗 Horário do bom dia",
        callback_data=f"adm:morningtime:{gid}"
    )

    b.button(
        text=(
            "🔴 Desligar boa noite"
            if g["night"]
            else "🌙 Ligar boa noite"
        ),
        callback_data=f"adm:night:{gid}"
    )

    b.button(
        text="🕙 Horário da boa noite",
        callback_data=f"adm:nighttime:{gid}"
    )

    b.button(text="🥇 Prêmio 1º lugar", callback_data=f"adm:prize1:{gid}")
    b.button(text="🥈 Prêmio 2º lugar", callback_data=f"adm:prize2:{gid}")
    b.button(text="🥉 Prêmio 3º lugar", callback_data=f"adm:prize3:{gid}")

    b.button(
        text="🧹 Encerrar desafio atual",
        callback_data=f"adm:cancel:{gid}"
    )

    season = season_status(gid)
    if season["status"] == "active":
        b.button(
            text="🏁 Encerrar temporada",
            callback_data=f"adm:week:{gid}"
        )
    else:
        b.button(
            text="🚀 Iniciar nova temporada",
            callback_data=f"adm:startweek:{gid}"
        )

    b.button(
        text="⬅️ Grupos",
        callback_data="adm:choose"
    )

    b.adjust(1)

    return b.as_markup()


# ============================================================
# TEXTO DO GRUPO
# ============================================================

def show_group_text(g):
    return (
        f"⚙️ <b>{escape(g['title'] or 'Grupo')}</b>\n\n"
        f"Interação: "
        f"{'🟢 ATIVA' if g['enabled'] else '🔴 DESATIVADA'}\n"
        f"🕙 Período: <b>{g['start_time']}</b> até "
        f"<b>{g['end_time']}</b>\n"
        f"🔁 Intervalo: <b>{g['challenge_interval']} min</b>\n"
        f"⭐ Pontos: <b>{g['challenge_points']}</b>\n"
        f"🖼️ Chance visual: <b>{g['image_chance']}%</b>\n"
        f"🌅 Bom dia: "
        f"{'🟢' if g['morning'] else '🔴'} "
        f"às <b>{g['morning_time']}</b>\n"
        f"🌙 Boa noite: "
        f"{'🟢' if g['night'] else '🔴'} "
        f"às <b>{g['night_time']}</b>\n"
        f"🎁 Prêmios TOP 3:\n"
        f"🥇 <b>{escape(g['prize1'] or g['prize'] or 'não configurado')}</b>\n"
        f"🥈 <b>{escape(g['prize2'] or 'não configurado')}</b>\n"
        f"🥉 <b>{escape(g['prize3'] or 'não configurado')}</b>\n\n"
        "Tudo acima pode ser alterado por este painel, "
        "sem editar o código."
    )


# ============================================================
# PERMISSÃO ADMIN
# ============================================================

async def require_admin(m):
    if not is_global_admin(m.from_user.id):
        from config import ADMIN_IDS
        if not ADMIN_IDS:
            await m.answer(
                "⚠️ <b>Painel ainda não configurado.</b>\n\n"
                "Defina seu ID na variável <code>ADMIN_IDS</code> do Discloud.\n"
                "Você pode descobrir seu ID usando /id."
            )
        else:
            await m.answer(
                "⛔ <b>Acesso negado.</b>\n\n"
                "Este usuário não está cadastrado como administrador.\n"
                "Confira a variável <code>ADMIN_IDS</code> no Discloud."
            )
        return False

    return True


async def require_callback(c):
    if not is_global_admin(c.from_user.id):
        await c.answer(
            "Sem permissão.",
            show_alert=True
        )
        return False

    return True


# ============================================================
# /ADMIN
# ============================================================

@router.message(Command("admin"))
async def panel(m: Message):

    if m.chat.type != "private":
        return await m.answer(
            "🔐 O painel administrativo funciona somente "
            "no <b>privado</b> do bot.\n\n"
            "Abra o privado e envie <b>/admin</b>."
        )

    if not await require_admin(m):
        return

    await m.answer(
        "🛠 <b>PAINEL ADMINISTRATIVO — PIT DIVERSÃO</b>\n\n"
        "Configure grupos, horários, desafios, pontos, "
        "prêmio e mensagens pelos botões:",
        reply_markup=home_kb()
    )


# ============================================================
# INTERAGIR AGORA
# ============================================================

def interact_groups_kb():
    b = InlineKeyboardBuilder()

    for g in all_groups():
        b.button(
            text=f"🐾 {(g['title'] or 'Grupo')[:30]}",
            callback_data=f"adm:ia:g:{g['id']}"
        )

    b.button(
        text="⬅️ Voltar",
        callback_data="adm:home"
    )

    b.adjust(1)

    return b.as_markup()


def interact_types_kb(gid):
    b = InlineKeyboardBuilder()

    items = [
        ("🎲 Aleatório", "random"),
        ("🧩 Charada", "charada"),
        ("❓ Pergunta", "pergunta"),
        ("🖼️ Desafio visual", "visual"),
        ("➗ Matemática", "matematica"),
        ("✅ Verdadeiro ou falso", "vf"),
    ]

    for label, kind in items:
        b.button(
            text=label,
            callback_data=f"adm:ia:t:{gid}:{kind}"
        )

    b.button(
        text="⬅️ Grupos",
        callback_data="adm:interact"
    )

    b.adjust(2, 2, 2, 1)

    return b.as_markup()


@router.callback_query(F.data == "adm:interact")
async def interact_admin(c):
    if not await require_callback(c):
        return

    groups = all_groups()

    if not groups:
        await safe_edit(
            c,
            "🎮 <b>🔥 DESAFIO RELÂMPAGO</b>\n\n"
            "Nenhum grupo está cadastrado ainda.",
            reply_markup=home_kb()
        )
    else:
        await safe_edit(
            c,
            "🎮 <b>🔥 DESAFIO RELÂMPAGO</b>\n\n"
            "Escolha o grupo onde o bot deve "
            "enviar a interação:",
            reply_markup=interact_groups_kb()
        )

    await c.answer()


@router.callback_query(F.data.startswith("adm:ia:g:"))
async def interact_choose_group(c):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[3])
    g = get(gid)

    if not g:
        return await c.answer(
            "Grupo não encontrado.",
            show_alert=True
        )

    await safe_edit(
        c,
        f"🎮 <b>🔥 DESAFIO RELÂMPAGO</b>\n\n"
        f"Grupo: <b>{escape(g['title'] or 'Grupo')}</b>\n\n"
        "Escolha o tipo de interação que será enviado agora:",
        reply_markup=interact_types_kb(gid)
    )

    await c.answer()


@router.callback_query(F.data.startswith("adm:ia:t:"))
async def interact_send(c):
    if not await require_callback(c):
        return

    parts = c.data.split(":", 4)

    gid = int(parts[3])
    kind = parts[4]

    g = get(gid)

    if not g:
        return await c.answer(
            "Grupo não encontrado.",
            show_alert=True
        )

    if not bool(g["enabled"]):
        return await c.answer(
            "A interação está desativada nesse grupo.",
            show_alert=True
        )

    from database.challenges import active

    if active(gid):
        return await c.answer(
            "Já existe um desafio ativo nesse grupo.",
            show_alert=True
        )

    points = max(
        1,
        int(g["challenge_points"] or 10)
    )

    if kind == "visual":

        from handlers.image_challenge import send_image_challenge

        ok = await send_image_challenge(
            c.bot,
            gid,
            points=points
        )

        if not ok:
            return await c.answer(
                "Não foi possível criar o desafio visual.",
                show_alert=True
            )

    else:

        from services.questions import choose_question

        category_map = {
            "charada": "Charada",
            "matematica": "Matemática",
            "vf": "V/F",
            "pergunta": [
                "Geral",
                "Futebol",
                "Filmes e séries",
                "Música",
                "Brasil",
                "Animais e natureza",
                "Engraçada"
            ],
        }

        category_filter = category_map.get(kind)

        try:
            category, question, answer, _pts, _options = await asyncio.to_thread(
                choose_question,
                gid,
                category=category_filter
            )
        except Exception:
            return await c.answer(
                "Não consegui gerar esse desafio agora. Tente novamente em alguns segundos.",
                show_alert=True
            )

        from handlers.challenge import send_text_challenge

        await send_text_challenge(
            c.bot,
            gid,
            category,
            question,
            answer,
            points,
            "🔥 DESAFIO RELÂMPAGO",
            _options
        )

    await safe_edit(
        c,
        f"🎮 <b>INTERAÇÃO ENVIADA!</b>\n\n"
        f"📍 Grupo: <b>{escape(g['title'] or 'Grupo')}</b>\n"
        f"🎯 Tipo: <b>{kind.title()}</b>\n"
        f"⭐ Valor: <b>{points} pontos</b>\n\n"
        "O desafio já foi enviado no grupo. "
        "O primeiro membro que acertar ganha.",
        reply_markup=home_kb()
    )

    await c.answer("Enviado para o grupo!")


# ============================================================
# VOLTAR PARA HOME
# ============================================================

@router.callback_query(F.data == "adm:home")
async def home(c):
    if not await require_callback(c):
        return

    await safe_edit(
        c,
        "🛠 <b>PAINEL ADMINISTRATIVO — PIT DIVERSÃO</b>\n\n"
        "Escolha uma opção:",
        reply_markup=home_kb()
    )

    await c.answer()


# ============================================================
# GRUPOS
# ============================================================

@router.callback_query(F.data == "adm:groups")
async def groups(c):
    if not await require_callback(c):
        return

    gs = all_groups()

    text = "👥 <b>GRUPOS CADASTRADOS</b>\n\n"

    if not gs:
        text += "Nenhum grupo registrado."
    else:
        for g in gs:
            text += (
                f"• {g['title'] or 'Grupo'} — "
                f"{'🟢 ativo' if g['enabled'] else '🔴 desligado'}\n"
            )

    b = InlineKeyboardBuilder()

    b.button(
        text="⚙️ Configurar",
        callback_data="adm:choose"
    )

    b.button(
        text="⬅️ Voltar",
        callback_data="adm:home"
    )

    b.adjust(1)

    await safe_edit(
        c,
        text,
        reply_markup=b.as_markup()
    )

    await c.answer()


# ============================================================
# ESCOLHER GRUPO
# ============================================================

@router.callback_query(F.data == "adm:choose")
async def choose(c):
    if not await require_callback(c):
        return

    await safe_edit(
        c,
        "⚙️ <b>ESCOLHA O GRUPO</b>\n\n"
        "Tudo será configurado individualmente:",
        reply_markup=group_kb()
    )

    await c.answer()


# ============================================================
# ABRIR CONFIGURAÇÃO DO GRUPO
# ============================================================

@router.callback_query(F.data.startswith("adm:g:"))
async def group(c):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])
    g = get(gid)

    if not g:
        return await c.answer(
            "Grupo não encontrado.",
            show_alert=True
        )

    await safe_edit(
        c,
        show_group_text(g),
        reply_markup=settings_kb(gid)
    )

    await c.answer()


# ============================================================
# ATUALIZAR TELA DO GRUPO
# ============================================================

async def refresh(c, gid, msg=""):
    g = get(gid)

    if not g:
        return

    text = show_group_text(g)

    if msg:
        text += f"\n\n✅ {msg}"

    await safe_edit(
        c,
        text,
        reply_markup=settings_kb(gid)
    )


# ============================================================
# LIGAR / DESLIGAR INTERAÇÃO
# ============================================================

@router.callback_query(F.data.startswith("adm:toggle:"))
async def toggle_cb(c):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    g = get(gid)

    if not g:
        return await c.answer(
            "Grupo não encontrado.",
            show_alert=True
        )

    toggle(
        gid,
        not bool(g["enabled"])
    )

    await refresh(
        c,
        gid,
        "Interação atualizada."
    )

    await c.answer()


# ============================================================
# BOM DIA
# ============================================================

@router.callback_query(F.data.startswith("adm:morning:"))
async def morning(c):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    g = get(gid)

    if not g:
        return await c.answer(
            "Grupo não encontrado.",
            show_alert=True
        )

    setting(
        gid,
        "morning",
        not bool(g["morning"])
    )

    await refresh(
        c,
        gid,
        "Bom dia atualizado."
    )

    await c.answer()


# ============================================================
# BOA NOITE
# ============================================================

@router.callback_query(F.data.startswith("adm:night:"))
async def night(c):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    g = get(gid)

    if not g:
        return await c.answer(
            "Grupo não encontrado.",
            show_alert=True
        )

    setting(
        gid,
        "night",
        not bool(g["night"])
    )

    await refresh(
        c,
        gid,
        "Boa noite atualizada."
    )

    await c.answer()


# ============================================================
# SOLICITAR CONFIGURAÇÃO
# ============================================================

async def ask(
    c,
    state,
    gid,
    kind,
    title,
    example
):
    await state.set_state(
        ConfigState.waiting
    )

    await state.update_data(
        group_id=gid,
        kind=kind
    )

    await c.message.answer(
        f"{title}\n\n"
        "Envie o valor.\n"
        f"Exemplo: <b>{example}</b>\n\n"
        "Envie <b>cancelar</b> para desistir."
    )

    await c.answer()


# ============================================================
# HORÁRIO DA INTERAÇÃO
# ============================================================

@router.callback_query(F.data.startswith("adm:hours:"))
async def hours(c, state):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    await ask(
        c,
        state,
        gid,
        "hours",
        "⏰ <b>HORÁRIO DA INTERAÇÃO</b>",
        "10:00-00:00"
    )


# ============================================================
# INTERVALO
# ============================================================

@router.callback_query(F.data.startswith("adm:interval:"))
async def interval(c, state):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    await ask(
        c,
        state,
        gid,
        "interval",
        "🔁 <b>INTERVALO DOS DESAFIOS</b>",
        "25"
    )


# ============================================================
# PONTOS
# ============================================================

@router.callback_query(F.data.startswith("adm:points:"))
async def points(c, state):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    await ask(
        c,
        state,
        gid,
        "points",
        "⭐ <b>PONTOS POR DESAFIO</b>",
        "10"
    )


# ============================================================
# CHANCE VISUAL
# ============================================================

@router.callback_query(F.data.startswith("adm:image:"))
async def image(c, state):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    await ask(
        c,
        state,
        gid,
        "image",
        "🖼️ <b>CHANCE DE DESAFIO VISUAL</b>",
        "35 (de 0 a 100)"
    )


# ============================================================
# HORÁRIO BOM DIA
# ============================================================

@router.callback_query(F.data.startswith("adm:morningtime:"))
async def morningtime(c, state):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    await ask(
        c,
        state,
        gid,
        "morningtime",
        "🕗 <b>HORÁRIO DO BOM DIA</b>",
        "08:00"
    )


# ============================================================
# HORÁRIO BOA NOITE
# ============================================================

@router.callback_query(F.data.startswith("adm:nighttime:"))
async def nighttime(c, state):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    await ask(
        c,
        state,
        gid,
        "nighttime",
        "🕙 <b>HORÁRIO DA BOA NOITE</b>",
        "22:00"
    )


# ============================================================
# PRÊMIO
# ============================================================

@router.callback_query(F.data.startswith("adm:prize:"))
async def prize_cb_legacy(c, state):
    # Compatibilidade com painéis antigos.
    if not await require_callback(c):
        return
    gid = int(c.data.split(":")[2])
    await ask(c, state, gid, "prize", "🎁 <b>PRÊMIO</b>", "R$ 50 no Pix")


@router.callback_query(F.data.startswith("adm:prize1:"))
async def prize1_cb(c, state):
    if not await require_callback(c): return
    gid = int(c.data.split(":")[2])
    await ask(c, state, gid, "prize1", "🥇 <b>PRÊMIO DO 1º LUGAR</b>", "R$ 100")


@router.callback_query(F.data.startswith("adm:prize2:"))
async def prize2_cb(c, state):
    if not await require_callback(c): return
    gid = int(c.data.split(":")[2])
    await ask(c, state, gid, "prize2", "🥈 <b>PRÊMIO DO 2º LUGAR</b>", "R$ 50")


@router.callback_query(F.data.startswith("adm:prize3:"))
async def prize3_cb(c, state):
    if not await require_callback(c): return
    gid = int(c.data.split(":")[2])
    await ask(c, state, gid, "prize3", "🥉 <b>PRÊMIO DO 3º LUGAR</b>", "R$ 25")


# ============================================================
# SALVAR CONFIGURAÇÕES
# ============================================================

@router.message(ConfigState.waiting)
async def save_config(
    m: Message,
    state: FSMContext
):

    if (
        m.chat.type != "private"
        or not is_global_admin(m.from_user.id)
    ):
        return

    text = (m.text or "").strip()

    if text.lower() == "cancelar":
        await state.clear()

        return await m.answer(
            "❌ Alteração cancelada.",
            reply_markup=home_kb()
        )

    data = await state.get_data()

    gid = data.get("group_id")
    kind = data.get("kind")

    # Envio manual de pontos pelo painel Admin.
    if kind == "send_points":
        try:
            value = int(text)
        except (TypeError, ValueError):
            return await m.answer("❌ Envie somente um número inteiro positivo.")
        if not 1 <= value <= 100000:
            return await m.answer("❌ A quantidade deve ficar entre 1 e 100000.")
        try:
            new_balance = add(
                int(gid),
                int(data["user_id"]),
                value,
                reason="Envio manual pelo painel Admin",
                actor_id=m.from_user.id,
            )
        except Exception:
            await state.clear()
            return await m.answer("❌ Não foi possível registrar os pontos. Nenhuma alteração foi confirmada.")
        await state.clear()
        return await m.answer(
            f"✅ <b>{value} pontos enviados!</b>\n\n"
            f"👤 Usuário: <code>{int(data['user_id'])}</code>\n"
            f"⭐ Novo saldo: <b>{new_balance} pontos</b>"
        )

    try:

        # HORÁRIO DA INTERAÇÃO
        if kind == "hours":

            if "-" not in text:
                raise ValueError

            a, b = [
                x.strip()
                for x in text.split("-", 1)
            ]

            a = parse_time(a)
            b = parse_time(b)

            if a is None or b is None:
                raise ValueError

            setting(
                gid,
                "start_time",
                a
            )

            setting(
                gid,
                "end_time",
                b
            )

            msg = "Horário da interação salvo."

        # INTERVALO
        elif kind == "interval":

            v = int(text)

            if not 1 <= v <= 1440:
                raise ValueError

            setting(
                gid,
                "challenge_interval",
                v
            )

            msg = "Intervalo salvo."

        # PONTOS
        elif kind == "points":

            v = int(text)

            if not 1 <= v <= 100000:
                raise ValueError

            setting(
                gid,
                "challenge_points",
                v
            )

            msg = "Pontuação salva."

        # CHANCE VISUAL
        elif kind == "image":

            v = int(text)

            if not 0 <= v <= 100:
                raise ValueError

            setting(
                gid,
                "image_chance",
                v
            )

            msg = "Chance visual salva."

        # HORÁRIOS BOM DIA / BOA NOITE
        elif kind in (
            "morningtime",
            "nighttime"
        ):

            value = parse_time(text)

            if value is None:
                raise ValueError

            column = {
                "morningtime": "morning_time",
                "nighttime": "night_time"
            }[kind]

            setting(
                gid,
                column,
                value
            )

            msg = "Horário salvo."

        # PRÊMIO
        elif kind in ("prize", "prize1", "prize2", "prize3"):

            if not text:
                raise ValueError

            if kind == "prize":
                prize(gid, text)
            else:
                setting(gid, kind, text)

            msg = "Prêmio salvo."

        else:
            raise ValueError

    except Exception:
        return await m.answer(
            "❌ Valor inválido.\n\n"
            "Confira o formato e tente novamente."
        )

    await state.clear()

    g = get(gid)

    await m.answer(
        show_group_text(g)
        + f"\n\n✅ {msg}",
        reply_markup=settings_kb(gid)
    )


# ============================================================
# PRÊMIOS
# ============================================================

@router.callback_query(F.data == "adm:prizes")
async def prizes(c):
    if not await require_callback(c):
        return

    gs = all_groups()

    text = "🎁 <b>PRÊMIOS DOS GRUPOS</b>\n\n"

    if not gs:
        text += "Nenhum grupo registrado."
    else:
        text += "".join(
            f"• {escape(g['title'] or 'Grupo')}: "
            f"<b>{escape(g['prize'] or 'não configurado')}</b>\n"
            for g in gs
        )

    await safe_edit(
        c,
        text,
        reply_markup=group_kb()
    )

    await c.answer()


# ============================================================
# STATUS GERAL
# ============================================================

@router.callback_query(F.data == "adm:status")
async def status(c):
    if not await require_callback(c):
        return

    gs = all_groups()

    active = sum(
        bool(g["enabled"])
        for g in gs
    )

    text = (
        "📊 <b>STATUS GERAL</b>\n\n"
        f"👥 Grupos: <b>{len(gs)}</b>\n"
        f"🟢 Interação ativa: <b>{active}</b>\n\n"
        "🤖 Os horários, intervalo, pontos, "
        "chance visual, bom dia, boa noite "
        "e prêmio são configuráveis pelo painel."
    )

    b = InlineKeyboardBuilder()

    b.button(
        text="⬅️ Voltar",
        callback_data="adm:home"
    )

    await safe_edit(
        c,
        text,
        reply_markup=b.as_markup()
    )

    await c.answer()


# ============================================================
# ENCERRAR DESAFIO
# ============================================================

@router.callback_query(F.data.startswith("adm:cancel:"))
async def cancel_cb(c):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])

    current=cancel(gid)
    if not current:
        return await c.answer("Não existe desafio ativo neste grupo.",show_alert=True)
    if current["message_id"]:
        try: await c.bot.delete_message(gid,int(current["message_id"]))
        except Exception: pass
    try: await c.bot.send_message(gid,"🧹 <b>DESAFIO ENCERRADO PELO ADMIN.</b>\n\nAguardando o próximo desafio. 🐶🔥")
    except Exception: pass
    await refresh(c,gid,"Desafio atual encerrado com sucesso.")
    await c.answer("Desafio encerrado com sucesso.")


# ============================================================
# SEMANA — FECHAMENTO MANUAL
# ============================================================

@router.callback_query(F.data.startswith("adm:week:"))
async def week_cb(c):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])
    g = get(gid)
    if not g:
        return await c.answer("Grupo não encontrado.", show_alert=True)

    prizes = [
        g["prize1"] or g["prize"] or "Prêmio não configurado",
        g["prize2"] or "Prêmio não configurado",
        g["prize3"] or "Prêmio não configurado",
    ]

    result = close_season(gid, prizes=prizes)
    if not result:
        return await c.answer(
            "A temporada já está encerrada ou ainda não possui pontuação.",
            show_alert=True,
        )

    rows = result["rows"]
    old_week = result["old_week"]
    medals = ["🥇", "🥈", "🥉"]

    with __import__("database.connection", fromlist=["db"]).db() as conn:
        participants = conn.execute(
            "SELECT COUNT(*) n FROM points WHERE group_id=? AND week=? AND points>0",
            (gid, old_week),
        ).fetchone()["n"]
        total_points = conn.execute(
            "SELECT COALESCE(SUM(points),0) total FROM points WHERE group_id=? AND week=?",
            (gid, old_week),
        ).fetchone()["total"]

    lines = [
        "🏆 <b>✨ TEMPORADA ENCERRADA! ✨</b>",
        "",
        f"📅 <b>Temporada:</b> {escape(old_week)}",
        f"👥 <b>Participantes com pontos:</b> {participants}",
        f"⭐ <b>Total de pontos conquistados:</b> {total_points}",
        "",
        "🏅 <b>RANKING FINAL</b>",
        "━━━━━━━━━━━━━━━━━━",
    ]

    for i in range(3):
        if i < len(rows):
            r = rows[i]
            name = escape(r["first_name"] or r["username"] or "Membro")
            lines.append(
                f'{medals[i]} <a href="tg://user?id={r["user_id"]}">{name}</a> — '
                f'<b>{r["points"]} pontos</b>'
            )
            lines.append(f"   🎁 Prêmio: <b>{escape(prizes[i])}</b>")
        else:
            lines.append(f"{medals[i]} — Sem participante")

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━",
        "🔒 <b>A temporada foi encerrada pelo administrador.</b>",
        "⭐ Os pontos desta temporada foram preservados no histórico.",
        "🚀 <b>Uma nova temporada ainda não foi iniciada.</b>",
        "👇 O administrador deverá usar o botão <b>Iniciar nova temporada</b> no painel.",
    ])

    try:
        await c.bot.send_message(gid, "\n".join(lines))
    except Exception:
        pass

    await c.answer("Temporada encerrada. O ranking foi publicado.", show_alert=True)
    await group(c)


@router.callback_query(F.data.startswith("adm:startweek:"))
async def start_week_cb(c):
    if not await require_callback(c):
        return

    gid = int(c.data.split(":")[2])
    result = start_new_season(gid)
    if not result:
        return await c.answer(
            "Encerre a temporada atual antes de iniciar uma nova.",
            show_alert=True,
        )

    new_week = result["new_week"]
    try:
        await c.bot.send_message(
            gid,
            "🚀 <b>NOVA TEMPORADA INICIADA!</b>\n\n"
            f"🏆 Temporada: <b>{escape(new_week)}</b>\n"
            "⭐ <b>Os pontos da nova temporada começam do zero.</b>\n"
            "📚 O ranking e o histórico da temporada anterior continuam preservados.\n\n"
            "🔥 Boa sorte a todos! A disputa começou novamente! 🐶🏆"
        )
    except Exception:
        pass

    await c.answer("Nova temporada iniciada com 0 pontos.", show_alert=True)
    await group(c)


# ============================================================
# USUÁRIOS E PONTOS
# ============================================================

def users_groups_kb():
    b = InlineKeyboardBuilder()
    for g in all_groups():
        b.button(
            text=f"👥 {(g['title'] or 'Grupo')[:30]}",
            callback_data=f"adm:users:g:{g['id']}",
        )
    b.button(text="⬅️ Voltar", callback_data="adm:home")
    b.adjust(1)
    return b.as_markup()


def users_list_kb(gid, page=0):
    b = InlineKeyboardBuilder()
    rows = users_with_points(gid, limit=10, offset=page * 10)
    for r in rows:
        label = escape((r["first_name"] or r["username"] or str(r["user_id"]))[:24])
        b.button(
            text=f"{label} — {r['points']} pts",
            callback_data=f"adm:user:{gid}:{r['user_id']}",
        )

    if page > 0:
        b.button(text="⬅️ Anterior", callback_data=f"adm:users:p:{gid}:{page-1}")
    if len(rows) == 10:
        b.button(text="Próxima ➡️", callback_data=f"adm:users:p:{gid}:{page+1}")
    b.button(text="⬅️ Grupos", callback_data="adm:users")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "adm:users")
async def users_panel(c):
    if not await require_callback(c):
        return
    gs = all_groups()
    if not gs:
        return await safe_edit(
            c,
            "👥 <b>USUÁRIOS / PONTOS</b>\n\nNenhum grupo cadastrado.",
            home_kb(),
        )
    await safe_edit(
        c,
        "👥 <b>USUÁRIOS / PONTOS</b>\n\nEscolha o grupo para visualizar os membros e seus pontos:",
        users_groups_kb(),
    )
    await c.answer()


@router.callback_query(F.data.startswith("adm:users:g:"))
async def users_group(c):
    if not await require_callback(c):
        return
    gid = int(c.data.split(":")[3])
    g = get(gid)
    if not g:
        return await c.answer("Grupo não encontrado.", show_alert=True)
    rows = users_with_points(gid, limit=10, offset=0)
    text = [
        f"👥 <b>USUÁRIOS — {escape(g['title'] or 'Grupo')}</b>",
        f"🏆 Temporada ativa: <b>{escape(active_week(gid))}</b>",
        "",
    ]
    if not rows:
        text.append("Nenhum membro cadastrado.")
    else:
        for i, r in enumerate(rows, 1):
            name = escape(r["first_name"] or r["username"] or "Membro")
            text.append(f"{i}. <a href=\"tg://user?id={r['user_id']}\">{name}</a> — <b>{r['points']} pts</b>")
        text.append("\n👇 Toque em um usuário para ver detalhes e enviar pontos.")
    await safe_edit(c, "\n".join(text), users_list_kb(gid, 0))
    await c.answer()


@router.callback_query(F.data.startswith("adm:users:p:"))
async def users_page(c):
    if not await require_callback(c):
        return
    _, _, _, gid_s, page_s = c.data.split(":")
    gid, page = int(gid_s), int(page_s)
    g = get(gid)
    if not g:
        return await c.answer("Grupo não encontrado.", show_alert=True)
    rows = users_with_points(gid, limit=10, offset=page * 10)
    text = [
        f"👥 <b>USUÁRIOS — {escape(g['title'] or 'Grupo')}</b>",
        f"🏆 Temporada ativa: <b>{escape(active_week(gid))}</b>",
        f"📄 Página {page+1}",
        "",
    ]
    for i, r in enumerate(rows, page * 10 + 1):
        name = escape(r["first_name"] or r["username"] or "Membro")
        text.append(f"{i}. <a href=\"tg://user?id={r['user_id']}\">{name}</a> — <b>{r['points']} pts</b>")
    await safe_edit(c, "\n".join(text), users_list_kb(gid, page))
    await c.answer()


@router.callback_query(F.data.startswith("adm:user:"))
async def user_detail(c):
    if not await require_callback(c):
        return
    _, _, gid_s, uid_s = c.data.split(":")
    gid, uid = int(gid_s), int(uid_s)
    g = get(gid)
    if not g:
        return await c.answer("Grupo não encontrado.", show_alert=True)

    rows = find_group_user(gid, uid)
    if not rows:
        return await c.answer("Usuário não encontrado neste grupo.", show_alert=True)
    r = rows[0]
    name = escape(r["first_name"] or r["username"] or "Membro")
    history = points_ledger(gid, uid, 8)
    summary = user_points_summary(gid, uid)
    lines = [
        "👤 <b>DETALHES DO USUÁRIO</b>",
        "",
        f"👤 {name}",
        f"🆔 <code>{uid}</code>",
        f"⭐ <b>Saldo atual: {summary['current']} pontos</b>",
        f"📊 <b>Total acumulado registrado: {summary['total']} pontos</b>",
        f"📅 Temporada: <b>{escape(active_week(gid))}</b>",
        "",
        "🧾 <b>ÚLTIMAS MOVIMENTAÇÕES</b>",
    ]
    if history:
        for h in history:
            sign = "+" if h["delta"] > 0 else ""
            lines.append(f"{sign}{h['delta']} → {h['balance']} pts — {escape(h['reason'])}")
    else:
        lines.append("Ainda não há histórico de movimentações nesta temporada.")
    if summary["seasons"]:
        lines.append("")
        lines.append("📚 <b>SALDOS POR TEMPORADA</b>")
        for season in summary["seasons"][:8]:
            lines.append(f"• {escape(season['week'])}: <b>{season['points']} pts</b>")
    b = InlineKeyboardBuilder()
    b.button(text="➕ Enviar pontos", callback_data=f"adm:send:{gid}:{uid}")
    b.button(text="🔄 Atualizar", callback_data=f"adm:user:{gid}:{uid}")
    b.button(text="⬅️ Usuários", callback_data=f"adm:users:g:{gid}")
    b.adjust(1)
    await safe_edit(c, "\n".join(lines), b.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("adm:send:"))
async def send_points_prompt(c, state: FSMContext):
    if not await require_callback(c):
        return
    _, _, gid_s, uid_s = c.data.split(":")
    gid, uid = int(gid_s), int(uid_s)
    if not find_group_user(gid, uid):
        return await c.answer("Usuário não encontrado.", show_alert=True)
    await state.set_state(ConfigState.waiting)
    await state.update_data(kind="send_points", group_id=gid, user_id=uid)
    await c.message.answer(
        "➕ <b>ENVIAR PONTOS</b>\n\n"
        f"Usuário: <code>{uid}</code>\n"
        "Digite somente a quantidade de pontos que deseja enviar.\n"
        "Ex.: <b>300</b>\n\n"
        "Digite <b>cancelar</b> para desistir."
    )
    await c.answer()


# ============================================================
# COMANDOS ANTIGOS
# ============================================================

@router.message(
    Command(
        "interagir",
        "bomdia_on",
        "bomdia_off",
        "boanoite_on",
        "boanoite_off",
        "premio",
        "limpardesafio",
        "fecharsemana",
        "anunciar"
    )
)
async def legacy_admin(m: Message):

    if m.chat.type != "private":
        return await m.answer(
            "🔐 Use <b>/admin</b> no privado do bot."
        )

    if not await require_admin(m):
        return

    await m.answer(
        "🛠 Abra <b>/admin</b> para configurar "
        "tudo pelos botões.",
        reply_markup=home_kb()
    )
