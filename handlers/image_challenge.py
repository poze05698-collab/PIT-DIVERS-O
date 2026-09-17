import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from database.users import upsert
from database.groups import upsert as upsert_group, member, enabled
from database.challenges import active, create, win
from database.points import add, mine
from services.image_challenge import make_number_image, make_count_image, make_odd_one_out_image

router = Router(name="image_challenge")


def keyboard(cid: int, numbers=range(1, 10)):
    numbers = list(numbers)
    rows = []
    for i in range(0, len(numbers), 3):
        rows.append([
            InlineKeyboardButton(text=str(n), callback_data=f"img:{cid}:{n}")
            for n in numbers[i:i + 3]
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_image_challenge(message_or_bot, chat_id: int, points: int = 15):
    if active(chat_id):
        return False

    kind = random.choice(["number", "count", "odd"])

    if kind == "number":
        answer = random.randint(1, 9)
        image = make_number_image(answer)
        question = "Qual número está na imagem?"
        caption = "❓ Qual número está na imagem?"
        buttons = range(1, 10)
    elif kind == "count":
        answer = random.randint(4, 12)
        image = make_count_image(answer)
        question = "Quantos círculos aparecem?"
        caption = "❓ Quantos círculos aparecem?"
        buttons = range(1, 13)
    else:
        image, answer = make_odd_one_out_image()
        question = "Qual posição é diferente?"
        caption = "❓ Qual posição é diferente? (1 a 9)"
        buttons = range(1, 10)

    points = max(1, int(points))
    cid = create(chat_id, question, str(answer), "Imagem", points)
    await message_or_bot.send_photo(
        chat_id=chat_id,
        photo=BufferedInputFile(image.getvalue(), filename="desafio_visual.png"),
        caption=(
            f"🖼️ <b>DESAFIO VISUAL #{cid}</b>\n\n"
            f"{caption}\n"
            f"⚡ O primeiro membro que acertar ganha <b>{points} pontos</b>!"
        ),
        reply_markup=keyboard(cid, buttons),
    )
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
        return await callback.answer("❌ Não é essa resposta!")

    # Atomic update in database: only the first correct click wins.
    if not win(cid, callback.from_user.id):
        return await callback.answer("⏱️ Alguém acertou primeiro!")

    upsert(callback.from_user)
    member(chat_id, callback.from_user.id)
    add(chat_id, callback.from_user.id, challenge["points"])

    name = (
        f"@{callback.from_user.username}"
        if callback.from_user.username
        else callback.from_user.first_name
    )
    await callback.answer("🎉 Você acertou primeiro!")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        f"🎉 <b>ACERTOU PRIMEIRO!</b>\n"
        f"👤 {name}\n"
        f"⭐ +{challenge['points']} pontos\n"
        f"🏆 Total na semana: {mine(chat_id, callback.from_user.id)}"
    )
