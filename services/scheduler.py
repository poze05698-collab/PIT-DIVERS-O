import asyncio,logging
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
from config import TIMEZONE,MORNING_HOUR,NIGHT_HOUR,AUTO_CHALLENGE_HOUR
from database.groups import all_groups
from database.points import previous_week,close_week
from database.challenges import active,create
from services.questions import QUESTIONS
log=logging.getLogger('scheduler')
async def scheduler_loop(bot:Bot):
 tz=ZoneInfo(TIMEZONE); seen=set()
 while True:
  try:
   n=datetime.now(tz); key=n.strftime('%Y-%m-%d-%H-%M')
   for g in all_groups():
    if g['enabled'] and n.minute==0:
     gkey=f'{g["id"]}:{key}'
     if n.hour==MORNING_HOUR and g['morning'] and gkey+':m' not in seen:
      await bot.send_message(g['id'],'🌅 <b>Bom dia, família PIT DIVERSÃO!</b> Que hoje seja leve, divertido e cheio de boas energias! 🔥'); seen.add(gkey+':m')
     if n.hour==NIGHT_HOUR and g['night'] and gkey+':n' not in seen:
      await bot.send_message(g['id'],'🌙 <b>Boa noite, família PIT DIVERSÃO!</b> Descansem bem. Amanhã tem mais! 😴✨'); seen.add(gkey+':n')
     if n.hour==AUTO_CHALLENGE_HOUR and gkey+':c' not in seen and not active(g['id']):
      import random
      if random.random() < 0.25:
       from handlers.image_challenge import send_image_challenge
       await send_image_challenge(bot, g['id'])
      else:
       q=random.choice(QUESTIONS); cid=create(g['id'],q[1],q[2],q[0],q[3]); await bot.send_message(g['id'],f'🧠 <b>DESAFIO AUTOMÁTICO #{cid}</b>\n\n🎯 {q[0]}\n❓ {q[1]}\n\n⚡ Primeiro a acertar ganha <b>{q[3]} pontos</b>!')
      seen.add(gkey+':c')
    if n.weekday()==6 and n.hour==23 and n.minute==59:
     r=close_week(g['id'],previous_week(),g['prize'] or 'Prêmio semanal não configurado')
     if r:
      name=f"@{r['username']}" if r['username'] else r['first_name']; await bot.send_message(g['id'],f'🏆 <b>SEMANA ENCERRADA!</b>\n\n🥇 {name}\n⭐ {r["points"]} pontos\n🎁 {r["prize"]}\n\n🔥 Nova semana iniciada!')
   if len(seen)>10000: seen.clear()
   if n.minute==0: seen.add(key)
  except Exception: log.exception('Erro no scheduler')
  await asyncio.sleep(30)
