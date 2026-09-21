import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo
from aiogram import Bot
from config import TIMEZONE
from database.groups import all_groups
from database.features import settings, expired_chest_messages, mark_chest_message_deleted
from database.points import season_is_active
from database.challenges import active, create, expired as expired_challenges
from services.questions import choose_question

log=logging.getLogger('scheduler')

WARNING_MESSAGES = [
    '⏰ <b>Faltam 15 minutos para o encerramento!</b> Aproveitem para garantir mais alguns pontos. 🔥',
    '🚨 <b>Últimos 15 minutos!</b> A interação está chegando ao fim por hoje. Bora pontuar! 🏆',
    '⌛ <b>15 minutos restantes!</b> Quem ainda não pontuou, essa é a hora. ⚡',
    '🔥 <b>Reta final!</b> Faltam só 15 minutos para fechar a interação de hoje!',
    '🏁 <b>Contagem regressiva:</b> 15 minutos para o encerramento. Boa sorte a todos! 🎯',
    '📣 <b>Atenção, grupo!</b> O fechamento de hoje acontece daqui a 15 minutos. Última chance de pontuar! 👑',
    '⚡ <b>Última chamada!</b> Restam 15 minutos de diversão antes do fechamento de hoje.',
    '🎮 <b>Reta final do dia!</b> Só mais 15 minutos. Corram atrás dos pontos! 🚀',
]

def hm(s, default):
    try:
        h,m=map(int,str(s or default).split(':'))
        if 0<=h<=23 and 0<=m<=59:return h*60+m
    except Exception: pass
    return default[0]*60+default[1]

def in_window(now_min,start,end):
    if start==end:return True
    if start<end:return start<=now_min<end
    return now_min>=start or now_min<end

def _closing_warning_due(now_local, end_min):
    target=(end_min-15) % 1440
    return now_local.hour*60+now_local.minute == target

def _warning_marker(gid, now_local):
    return f'{gid}:{now_local.date().isoformat()}'

def _warning_already_sent(gid, day):
    from database.connection import db
    with db() as c:
        return c.execute('SELECT 1 FROM group_closing_warnings WHERE group_id=? AND day=?',(gid,day)).fetchone() is not None

def _mark_warning_sent(gid, day):
    from database.connection import db
    with db() as c:
        c.execute('INSERT OR IGNORE INTO group_closing_warnings(group_id,day,created) VALUES(?,?,?)',(gid,day,datetime.now(timezone.utc).isoformat()))

async def _automatic_challenge(bot, group):
    gid=group['id']
    if active(gid):return
    chance=max(0,min(100,int(group['image_chance'] or 35)))
    if random.randint(1,100)<=chance:
        try:
            from handlers.image_challenge import send_image_challenge
            await send_image_challenge(bot,gid,points=10)
            return
        except Exception:
            log.exception('Falha ao gerar desafio visual no grupo %s',gid)
    category,question,answer,_,options=await asyncio.to_thread(choose_question,gid)
    points=10
    from handlers.challenge import send_text_challenge
    await send_text_challenge(bot,gid,category,question,answer,points,'DESAFIO AUTOMÁTICO', options)

async def _cleanup(bot):
    try:
        for row in expired_challenges():
            if row['message_id']:
                try:
                    await bot.delete_message(row['group_id'], row['message_id'])
                except Exception:
                    pass
    except Exception:
        log.exception('Falha na limpeza de desafios expirados')
    try:
        from database.connection import db
        current=datetime.now(timezone.utc).isoformat()
        with db() as c:
            c.execute(
                "UPDATE memory_games SET status='expired' WHERE status='active' AND expires IS NOT NULL AND expires<=?",
                (current,),
            )
    except Exception:
        log.exception('Falha na limpeza de jogos de memória expirados')
    try:
        for release_id, gid, message_id in expired_chest_messages():
            try:
                await bot.delete_message(gid, message_id)
            except Exception:
                log.warning('Não foi possível apagar postagem do baú %s no grupo %s', message_id, gid)
            finally:
                mark_chest_message_deleted(release_id)
    except Exception:
        log.exception('Falha na limpeza de baús expirados')

async def scheduler_loop(bot:Bot):
    tz=ZoneInfo(TIMEZONE); seen=set()
    while True:
        try:
            now=datetime.now(tz); now_min=now.hour*60+now.minute; minute_key=now.strftime('%Y-%m-%d-%H-%M')
            await _cleanup(bot)
            groups=all_groups()
            async def process_group(g):
                gid=g['id']
                if not bool(g['enabled']): return
                season_open = season_is_active(gid)
                start=hm(g['start_time'],(10,0)); end=hm(g['end_time'],(0,0))
                inside=in_window(now_min,start,end)

                # Aviso único por dia, exatamente 15 min antes do horário de fechamento.
                if _closing_warning_due(now,end):
                    warning_day=_warning_marker(gid,now)
                    if not _warning_already_sent(gid, warning_day):
                        try:
                            await bot.send_message(gid, random.choice(WARNING_MESSAGES))
                            _mark_warning_sent(gid, warning_day)
                        except Exception:
                            log.exception('Falha no aviso de encerramento do grupo %s',gid)

                if now_min==hm(g['morning_time'],(8,0)) and bool(g['morning']):
                    marker=f'{gid}:{minute_key}:morning'
                    if marker not in seen:
                        await bot.send_message(gid,'🌅 <b>Bom dia, família PIT DIVERSÃO!</b>\nQue hoje seja leve, divertido e cheio de boas energias! 🔥');seen.add(marker)
                if now_min==hm(g['night_time'],(22,0)) and bool(g['night']):
                    marker=f'{gid}:{minute_key}:night'
                    if marker not in seen:
                        await bot.send_message(gid,'🌙 <b>Boa noite, família PIT DIVERSÃO!</b>\nDescansem bem. Amanhã tem mais diversão! 😴✨');seen.add(marker)

                # Eventos e desafios só rodam dentro da janela configurada.
                if season_open and inside and bool(settings(gid)['events_enabled']) and random.randint(1,180)==1:
                    from database.connection import db
                    with db() as c:
                        c.execute('UPDATE events SET active=0 WHERE group_id=?',(gid,))
                        c.execute('INSERT INTO events(group_id,type,ends,multiplier,active) VALUES(?,?,?,?,1)',(gid,'surpresa',(now+timedelta(minutes=15)).astimezone(timezone.utc).isoformat(),int(settings(gid)['event_multiplier'])))
                    await bot.send_message(gid,f'🎉 <b>EVENTO SURPRESA!</b>\nPelos próximos 15 minutos, os pontos dos acertos valem <b>x{settings(gid)["event_multiplier"]}</b>! 🔥')
                if not inside or not season_open: return
                interval=max(1,int(g['challenge_interval'] or 25))
                # Intervalo contado a partir do início, inclusive em janelas que atravessam meia-noite.
                elapsed=(now_min-start)%1440
                if elapsed % interval==0:
                    marker=f'{gid}:{minute_key}:challenge'
                    if marker not in seen:
                        try:
                            await _automatic_challenge(bot,g)
                        except Exception:
                            log.exception('Falha no desafio automático do grupo %s',gid)
                        seen.add(marker)

            await asyncio.gather(*(process_group(g) for g in groups), return_exceptions=True)

            # O encerramento de temporada é EXCLUSIVAMENTE manual pelo painel Admin.
            # Não existe mais fechamento automático por domingo/horário.

            if len(seen)>20000: seen.clear()
        except Exception:
            log.exception('Erro no scheduler')
        await asyncio.sleep(20)
