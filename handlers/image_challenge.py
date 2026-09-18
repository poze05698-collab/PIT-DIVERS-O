import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from database.users import upsert
from database.groups import upsert as upsert_group, member, enabled
from database.challenges import active, create, win
from database.points import add, mine
from database.features import award, victory, spam_ok, reset_combo
from services.image_challenge import (
    make_number_image, make_count_image, make_odd_one_out_image,
    make_color_image, make_sequence_image, VISUAL_CHALLENGES
)

router = Router(name="image_challenge")


def keyboard(cid: int, numbers):
    numbers = list(numbers)
    rows = []
    for i in range(0, len(numbers), 3):
        rows.append([
            InlineKeyboardButton(
                text=str(n),
                callback_data=f"img:{cid}:{n}"
            )
            for n in numbers[i:i+3]
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _number_options(answer: int):
    values = {answer}
    delta = 1
    while len(values) < 5:
        for sign in (-1, 1):
            v = answer + sign * delta
            if v > 0:
                values.add(v)
        delta += 1
    return sorted(values)


def _color_options():
    return [
        "🔵 AZUL",
        "🟢 VERDE",
        "🔴 VERMELHO",
        "🟡 AMARELO",
        "🟣 ROXO",
    ]


async def send_image_challenge(message_or_bot, chat_id: int, points: int = 15):
    if active(chat_id):
        return False

    preset = random.choice(VISUAL_CHALLENGES)
    kind = preset["kind"]
    value = int(preset["value"])

    if kind == "number":
        answer = value
        image = make_number_image(answer)
        question = "Qual número aparece na imagem?"
        buttons = _number_options(answer)

    elif kind == "count":
        answer = value
        image = make_count_image(answer, seed=int(preset["id"]))
        question = "Quantos círculos aparecem?"
        buttons = list(range(1, 19))

    elif kind == "odd":
        image, answer = make_odd_one_out_image(seed=int(preset["id"]))
        question = "Qual é a posição do símbolo diferente?"
        buttons = list(range(1, 10))

    elif kind == "color":
        answer = value
        image = make_color_image(answer, seed=int(preset["id"]))
        question = "Qual é a cor da figura?"
        # callback recebe índice; a resposta armazenada também é índice.
        buttons = list(range(5))

    else:
        answer = value
        image = make_sequence_image(answer, seed=int(preset["id"]), start=preset.get("start"), step=preset.get("step"))
        question = "Qual número completa a sequência?"
        buttons = _number_options(answer)

    points = max(1, int(points))
    cid = create(chat_id, question, str(answer), "Visual", points)

    if kind == "color":
        labels = _color_options()
        rows = []
        for i in range(0, 5, 2):
            rows.append([
                InlineKeyboardButton(text=labels[j], callback_data=f"img:{cid}:{j}")
                for j in range(i, min(i+2, 5))
            ])
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
    else:
        markup = keyboard(cid, buttons)

    caption = (
        f"🖼️ <b>DESAFIO VISUAL #{cid}</b>\n\n"
        f"🎯 {question}\n\n"
        f"⚡ <b>O primeiro a acertar ganha {points} pontos!</b>\n"
        f"👇 Escolha uma opção:"
    )

    sent=await message_or_bot.send_photo(
        chat_id=chat_id,
        photo=BufferedInputFile(
            image.getvalue(),
            filename="desafio_visual.png"
        ),
        caption=caption,
        reply_markup=markup,
        # O Telegram esconde a imagem até o usuário tocar nela.
        has_spoiler=True,
    )
    from database.challenges import set_message_id
    set_message_id(cid,sent.message_id)
    return True


@router.message(Command("imagem"))
async def imagem(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return await message.answer("🖼️ Este desafio funciona em grupos.")
    if not enabled(message.chat.id):
        return await message.answer("🐾 A interação está desativada. Um admin deve usar /pit.")
    upsert(message.from_user)
    upsert_group(message.chat)
    member(message.chat.id, message.from_user.id)
    if active(message.chat.id):
        return await message.answer("⏳ Já existe um desafio ativo neste grupo.")
    await send_image_challenge(message.bot, message.chat.id)


@router.callback_query(F.data.startswith("img:"))
async def answer_image(callback: CallbackQuery):
    try:
        _, cid_s, answer_s = callback.data.split(":")
        cid = int(cid_s)
        answer = int(answer_s)
    except (ValueError, AttributeError):
        return await callback.answer("Desafio inválido.")

    if not callback.message:
        return await callback.answer("Mensagem do desafio não encontrada.")

    chat_id = callback.message.chat.id
    challenge = active(chat_id)
    if not challenge or challenge["id"] != cid:
        return await callback.answer("⏱️ Este desafio já terminou.")

    if str(answer) != str(challenge["answer"]):
        return await callback.answer("❌ Não é essa resposta!", show_alert=False)

    if not win(cid, callback.from_user.id):
        return await callback.answer("⏱️ Alguém acertou primeiro!")

    upsert(callback.from_user)
    member(chat_id, callback.from_user.id)
    add(chat_id, callback.from_user.id, challenge["points"])
    fx = award(chat_id, callback.from_user.id, challenge["points"], "Visual")
    if fx["bonus"]: add(chat_id, callback.from_user.id, fx["bonus"])
    total = mine(chat_id, callback.from_user.id)

    name = (
        f"@{callback.from_user.username}"
        if callback.from_user.username
        else callback.from_user.first_name
    )

    await callback.answer("🎉 Você acertou primeiro!")

    try:
        await callback.message.delete()
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    await callback.message.answer(
        f"{victory(chat_id)}\n\n"
        f"👑 {name}\n"
        f"⭐ <b>+{challenge['points']} pontos</b>\n"
        f"🏆 Total na semana: <b>{total} pontos</b>" + (f"\n🔥 Combo: <b>{fx['combo']}</b>" if fx["combo"] else "")
    )
