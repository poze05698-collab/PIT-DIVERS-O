import asyncio
import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
from config import TIMEZONE
from database.groups import all_groups
from database.points import previous_week, close_week
from database.challenges import active, create, cancel
from services.questions import QUESTIONS

log=logging.getLogger('scheduler')

def hm(s, default):
    try:
        h,m=map(int,str(s or default).split(':'))
        if 0<=h<=23 and 0<=m<=59:return h*60+m
    except Exception: pass
    return default[0]*60+default[1]

def in_window(now_min,start,end):
    # end=00:00 means the daily window ends exactly at midnight.
    if start==end:return True
    if start<end:return start<=now_min<end
    return now_min>=start or now_min<end


async def _automatic_challenge(bot, group):
    gid=group['id']
    if active(gid):return
    chance=max(0,min(100,int(group['image_chance'] or 35)))
    if random.randint(1,100)<=chance:
        try:
            from handlers.image_challenge import send_image_challenge
            await send_image_challenge(bot,gid,points=int(group['challenge_points'] or 10))
            return
        except Exception:
            log.exception('Falha ao gerar desafio visual no grupo %s',gid)
    category,question,answer,_=random.choice(QUESTIONS)
    points=max(1,int(group['challenge_points'] or 10))
    from handlers.challenge import send_text_challenge
    await send_text_challenge(bot,gid,category,question,answer,points,'DESAFIO AUTOMÁTICO')

async def scheduler_loop(bot:Bot):
    tz=ZoneInfo(TIMEZONE); seen=set()
    while True:
        try:
            now=datetime.now(tz); now_min=now.hour*60+now.minute; minute_key=now.strftime('%Y-%m-%d-%H-%M')
            for g in all_groups():
                gid=g['id']
                if not bool(g['enabled']):continue
                start=hm(g['start_time'],(10,0)); end=hm(g['end_time'],(0,0))
                inside=in_window(now_min,start,end)
                # Bom dia/boa noite are independent of the interaction window.
                if now_min==hm(g['morning_time'],(8,0)) and bool(g['morning']):
                    marker=f'{gid}:{minute_key}:morning'
                    if marker not in seen:
                        await bot.send_message(gid,'🌅 <b>Bom dia, família PIT DIVERSÃO!</b>\nQue hoje seja leve, divertido e cheio de boas energias! 🔥');seen.add(marker)
                if now_min==hm(g['night_time'],(22,0)) and bool(g['night']):
                    marker=f'{gid}:{minute_key}:night'
                    if marker not in seen:
                        await bot.send_message(gid,'🌙 <b>Boa noite, família PIT DIVERSÃO!</b>\nDescansem bem. Amanhã tem mais diversão! 😴✨');seen.add(marker)
                # Outside the configured interaction window, the bot sends no challenges.
                if not inside:
                    if active(gid) and now_min==end:
                        cancel(gid)
                    continue
                interval=max(1,int(g['challenge_interval'] or 25))
                # Anchored to start time: with 10:00 + 25 min => 10:00, 10:25, 10:50, 11:15...
                if (now_min-start)%interval==0:
                    marker=f'{gid}:{minute_key}:challenge'
                    if marker not in seen:
                        await _automatic_challenge(bot,g);seen.add(marker)
                # Sunday at 23:59 closes the ISO week. The next week's points are untouched.
                if now.weekday()==6 and now.hour==23 and now.minute==59:
                    marker=f'{gid}:{minute_key}:week'
                    if marker not in seen:
                        result=close_week(gid,previous_week(),g['prize'] or 'Prêmio não configurado')
                        if result:
                            name=f"@{result['username']}" if result['username'] else result['first_name']
                            await bot.send_message(gid,f'🏆 <b>SEMANA ENCERRADA!</b>\n\n🥇 {name}\n⭐ {result["points"]} pontos\n🎁 {result["prize"]}\n\n🔥 Nova semana iniciada!')
                        seen.add(marker)
            if len(seen)>20000:seen.clear()
        except Exception:log.exception('Erro no scheduler')
        await asyncio.sleep(20)
