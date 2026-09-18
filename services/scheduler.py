import asyncio
import logging
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiogram import Bot
from config import TIMEZONE
from database.groups import all_groups
from database.points import previous_week, close_week
from database.features import close_season, top3, settings, expire_chests
from database.challenges import active, create
from services.questions import choose_question

log=logging.getLogger('scheduler')
CLOSE_WARNING_MINUTES=15
CLOSE_MESSAGES=[
'🌙 <b>Atenção, família PIT DIVERSÃO!</b>\nFaltam poucos minutos para encerrarmos o grupo por hoje. Aproveitem os últimos minutos! 🔥',
'⏰ <b>Última chamada!</b>\nO PIT DIVERSÃO fecha em breve. Quem ainda quiser participar, é agora! 🐶🔥',
'🔔 <b>Estamos chegando ao fim de hoje!</b>\nDaqui a pouco o grupo será encerrado. Obrigado pela diversão! 🌙',
'🐶 <b>O PITBULL já está preparando o descanso...</b>\nFaltam poucos minutos para fechar o grupo. Até amanhã! 🌙',
'🔥 <b>Últimos minutos de diversão!</b>\nO horário de fechamento está chegando. Corram para aproveitar! ⏳'
]

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
    category,question,answer,_,options=await asyncio.to_thread(choose_question,gid)
    points=max(1,int(group['challenge_points'] or 10))
    from handlers.challenge import send_text_challenge
    await send_text_challenge(bot,gid,category,question,answer,points,'DESAFIO AUTOMÁTICO', options)

async def scheduler_loop(bot:Bot):
    tz=ZoneInfo(TIMEZONE); seen=set()
    while True:
        try:
            now=datetime.now(tz); now_min=now.hour*60+now.minute; minute_key=now.strftime('%Y-%m-%d-%H-%M')
            async def process_group(g):
                gid=g['id']
                if not bool(g['enabled']): return
                start=hm(g['start_time'],(10,0)); end=hm(g['end_time'],(0,0))
                inside=in_window(now_min,start,end)
                warning_min=(end-CLOSE_WARNING_MINUTES)%1440
                if now_min==warning_min:
                    marker=f'{gid}:{now.date().isoformat()}:close-warning'
                    if marker not in seen:
                        try:
                            await bot.send_message(gid,CLOSE_MESSAGES[(now.date().toordinal()+abs(int(gid))) % len(CLOSE_MESSAGES)])
                        except Exception:
                            log.exception('Falha ao enviar aviso de fechamento no grupo %s',gid)
                        seen.add(marker)
                if now_min==hm(g['morning_time'],(8,0)) and bool(g['morning']):
                    marker=f'{gid}:{minute_key}:morning'
                    if marker not in seen:
                        await bot.send_message(gid,'🌅 <b>Bom dia, família PIT DIVERSÃO!</b>\nQue hoje seja leve, divertido e cheio de boas energias! 🔥');seen.add(marker)
                if now_min==hm(g['night_time'],(22,0)) and bool(g['night']):
                    marker=f'{gid}:{minute_key}:night'
                    if marker not in seen:
                        await bot.send_message(gid,'🌙 <b>Boa noite, família PIT DIVERSÃO!</b>\nDescansem bem. Amanhã tem mais diversão! 😴✨');seen.add(marker)
                # Limpeza leve de estados temporários; não toca em histórico nem pontuação.
                try:
                    from database.connection import db
                    with db() as c:
                        c.execute("UPDATE events SET active=0 WHERE group_id=? AND active=1 AND ends<=?",(gid,now.astimezone(__import__('datetime').timezone.utc).isoformat()))
                except Exception:
                    log.exception('Falha na limpeza de estados do grupo %s',gid)
                if bool(settings(gid)['events_enabled']) and random.randint(1,180)==1:
                    from database.connection import db
                    with db() as c:
                        c.execute('UPDATE events SET active=0 WHERE group_id=?',(gid,))
                        c.execute('INSERT INTO events(group_id,type,ends,multiplier,active) VALUES(?,?,?,?,1)',(gid,'surpresa',(now+timedelta(minutes=15)).astimezone(__import__('datetime').timezone.utc).isoformat(),int(settings(gid)['event_multiplier'])))
                    await bot.send_message(gid,f'🎉 <b>EVENTO SURPRESA!</b>\nPelos próximos 15 minutos, os pontos dos acertos valem <b>x{settings(gid)["event_multiplier"]}</b>! 🔥')
                if not inside: return
                interval=max(1,int(g['challenge_interval'] or 25))
                if (now_min-start)%interval==0:
                    marker=f'{gid}:{minute_key}:challenge'
                    if marker not in seen:
                        try:
                            await _automatic_challenge(bot,g)
                            seen.add(marker)
                        except Exception:
                            log.exception('Falha no desafio automático do grupo %s',gid)
                if now.weekday()==6 and now.hour==23 and now.minute==59:
                    marker=f'{gid}:{minute_key}:week'
                    if marker not in seen:
                        prizes=[g['prize1'] or g['prize'] or 'Prêmio não configurado',g['prize2'] or 'Prêmio não configurado',g['prize3'] or 'Prêmio não configurado']
                        rows=close_season(gid, __import__('database.points',fromlist=['wk']).wk(), prizes)
                        if rows:
                            medals=['🥇','🥈','🥉']; lines=['🏆 <b>SEMANA ENCERRADA!</b>','']
                            for i,r in enumerate(rows): lines.append(f'{medals[i]} <a href=\"tg://user?id={r["user_id"]}\">{r["first_name"] or "Membro"}</a> — <b>{r["points"]} pts</b>\n🎁 {prizes[i]}')
                            lines.append('\n🔥 Nova semana iniciada!')
                            await bot.send_message(gid,'\n'.join(lines))
                        seen.add(marker)

            expired=expire_chests()
            for _rid,_gid,_mid in expired:
                try:
                    await bot.delete_message(_gid,_mid)
                except Exception:
                    log.info('Postagem de baú %s no grupo %s já não podia ser apagada.',_mid,_gid)
            results=await asyncio.gather(*(process_group(g) for g in all_groups()), return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.error('Falha isolada no processamento de um grupo: %s', result, exc_info=(type(result), result, result.__traceback__))
            if len(seen)>20000:seen.clear()
        except Exception:log.exception('Erro no scheduler')
        await asyncio.sleep(20)
