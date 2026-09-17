import asyncio
import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot

from config import TIMEZONE, MORNING_HOUR, NIGHT_HOUR, AUTO_CHALLENGE_HOUR
from database.groups import all_groups
from database.points import previous_week, close_week
from database.challenges import active, create
from services.questions import QUESTIONS

log = logging.getLogger("scheduler")


async def _automatic_challenge(bot: Bot, group_id: int):
    """Create a challenge without requiring the admin to add one."""
    if active(group_id):
        return

    # Image challenges are generated locally; no image API/key is required.
    if random.random() < 0.35:
        try:
            from handlers.image_challenge import send_image_challenge
            await send_image_challenge(bot, group_id)
            return
        except Exception:
            log.exception("Falha ao gerar desafio visual no grupo %s", group_id)

    category, question, answer, points = random.choice(QUESTIONS)
    cid = create(group_id, question, answer, category, points)
    await bot.send_message(
        group_id,
        f"🧠 <b>DESAFIO AUTOMÁTICO #{cid}</b>\n\n"
        f"🎯 Categoria: <b>{category}</b>\n"
        f"❓ {question}\n\n"
        f"⚡ Primeiro a acertar ganha <b>{points} pontos</b>!",
    )


async def scheduler_loop(bot: Bot):
    """Runs independently so a failure in one group never kills the scheduler."""
    tz = ZoneInfo(TIMEZONE)
    seen = set()

    while True:
        try:
            now = datetime.now(tz)
            minute_key = now.strftime("%Y-%m-%d-%H-%M")

            for group in all_groups():
                group_id = group["id"]

                # The migration guarantees these columns.  Keep defensive
                # fallbacks so one legacy/malformed row cannot stop scheduling.
                keys = group.keys()
                enabled_value = group["enabled"] if "enabled" in keys else (group["entertainment_enabled"] if "entertainment_enabled" in keys else 1)
                morning_value = group["morning"] if "morning" in keys else (group["morning_enabled"] if "morning_enabled" in keys else 1)
                night_value = group["night"] if "night" in keys else (group["night_enabled"] if "night_enabled" in keys else 1)
                prize_value = group["prize"] if "prize" in keys else (group["weekly_prize"] if "weekly_prize" in keys else "")

                if not bool(enabled_value):
                    continue

                group_key = f"{group_id}:{minute_key}"

                if now.minute == 0:
                    if now.hour == MORNING_HOUR and bool(morning_value):
                        marker = group_key + ":morning"
                        if marker not in seen:
                            await bot.send_message(
                                group_id,
                                "🌅 <b>Bom dia, família PIT DIVERSÃO!</b>\n"
                                "Que hoje seja leve, divertido e cheio de boas energias! 🔥",
                            )
                            seen.add(marker)

                    if now.hour == NIGHT_HOUR and bool(night_value):
                        marker = group_key + ":night"
                        if marker not in seen:
                            await bot.send_message(
                                group_id,
                                "🌙 <b>Boa noite, família PIT DIVERSÃO!</b>\n"
                                "Descansem bem. Amanhã tem mais diversão! 😴✨",
                            )
                            seen.add(marker)

                    if now.hour == AUTO_CHALLENGE_HOUR:
                        marker = group_key + ":challenge"
                        if marker not in seen:
                            await _automatic_challenge(bot, group_id)
                            seen.add(marker)

                # Close the previous week once, at Sunday 23:59.
                if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
                    marker = group_key + ":week"
                    if marker not in seen:
                        prize = prize_value or "Prêmio semanal não configurado"
                        result = close_week(group_id, previous_week(), prize)
                        if result:
                            name = (
                                f"@{result['username']}"
                                if result["username"]
                                else result["first_name"]
                            )
                            await bot.send_message(
                                group_id,
                                "🏆 <b>SEMANA ENCERRADA!</b>\n\n"
                                f"🥇 {name}\n"
                                f"⭐ {result['points']} pontos\n"
                                f"🎁 {result['prize']}\n\n"
                                "🔥 Nova semana iniciada!",
                            )
                        seen.add(marker)

            # Prevent the in-memory marker set from growing forever.
            if len(seen) > 10000:
                seen.clear()

        except Exception:
            # The scheduler stays alive even if Telegram rejects one message
            # or an individual database row has an unexpected value.
            log.exception("Erro no scheduler")

        await asyncio.sleep(30)
