import random
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from database.users import upsert
from database.groups import upsert as upsert_group, member
from database.groups import enabled
from database.challenges import active, create, win
from database.points import add, mine
from services.image_challenge import make_number_image

router = Router(name="image_challenge")

def keyboard(cid: int):
    numbers = list(range(1, 10))
    rows = []
    for i in range(0, 9, 3):
        rows.append([
            InlineKeyboardButton(text=str(n), callback_data=f"img:{cid}:{n}")
            for n in numbers[i:i+3]
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def send_image_challenge(message_or_bot, chat_id: int):
    c = active(chat_id)
    if c:
        return False

    number = random.randint(1, 9)
    question = "Qual número está na imagem?"
    cid = create(chat_id, question, str(number), "Imagem", 15)

    image = make_number_image(number)
    await message_or_bot.send_photo(
        chat_id=chat_id,
        photo=BufferedInputFile(image.getvalue(), filename="desafio_numero.png"),
        caption=(
            f"🖼️ <b>DESAFIO VISUAL #{cid}</b>\n\n"
            "❓ Qual número está na imagem?\n"
            "⚡ O primeiro membro que acertar ganha <b>15 pontos</b>!"
        ),
        reply_markup=keyboard(cid),
    )
    return True

@router.message(Command("imagem"))
async def imagem(m: Message):
    if m.chat.type not in {"group", "supergroup"}:
        return await m.answer("🖼️ Este desafio funciona em grupos.")
    if not enabled(m.chat.id):
        return await m.answer("🐾 A interação está desativada.")
    upsert(m.from_user)
    upsert_group(m.chat)
    member(m.chat.id, m.from_user.id)
    if active(m.chat.id):
        return await m.answer("⏳ Já existe um desafio ativo neste grupo.")
    await send_image_challenge(m.bot, m.chat.id)

@router.callback_query(F.data.startswith("img:"))
async def answer_image(callback: CallbackQuery):
    try:
        _, cid_s, answer_s = callback.data.split(":")
        cid = int(cid_s)
        answer = int(answer_s)
    except (ValueError, AttributeError):
        return await callback.answer("Desafio inválido.")

    c = active(callback.message.chat.id)
    if not c or c["id"] != cid:
        return await callback.answer("⏱️ Este desafio já terminou.")

    if str(answer) != str(c["answer"]):
        return await callback.answer("❌ Não é esse número!")

    # Atomic DB update ensures only the first correct member wins.
    if not win(cid, callback.from_user.id):
        return await callback.answer("⏱️ Alguém acertou primeiro!")

    upsert(callback.from_user)
    member(callback.message.chat.id, callback.from_user.id)
    add(callback.message.chat.id, callback.from_user.id, c["points"])

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
        f"⭐ +{c['points']} pontos\n"
        f"🏆 Total na semana: {mine(callback.message.chat.id, callback.from_user.id)}"
    )
