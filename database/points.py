from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from config import TIMEZONE
from database.connection import db
def now(): return datetime.now(timezone.utc).isoformat()
def wk(dt=None):
    if dt is None: d=datetime.now(ZoneInfo(TIMEZONE)).date()
    else:
        try: d=dt.astimezone(ZoneInfo(TIMEZONE)).date()
        except Exception: d=dt.date()
    y,w,_=d.isocalendar(); return f'{y}-W{w:02d}'
def add(g,u,n):
    with db() as c:c.execute("INSERT INTO points VALUES(?,?,?,?,?) ON CONFLICT(group_id,user_id,week) DO UPDATE SET points=points+excluded.points,updated=excluded.updated",(g,u,wk(),n,now()))
def mine(g,u):
    with db() as c:
        r=c.execute('SELECT points FROM points WHERE group_id=? AND user_id=? AND week=?',(g,u,wk())).fetchone(); return r['points'] if r else 0
def rank(g,limit=10,week=None):
    with db() as c:return c.execute("SELECT p.user_id,p.points,u.first_name,u.username FROM points p JOIN users u ON u.id=p.user_id WHERE p.group_id=? AND p.week=? ORDER BY p.points DESC,p.updated ASC LIMIT ?",(g,week or wk(),limit)).fetchall()
def close_week(g,week,prize):
    with db() as c:
        if c.execute('SELECT 1 FROM weekly_winners WHERE group_id=? AND week=?',(g,week)).fetchone(): return None
        r=c.execute("SELECT p.user_id,p.points,u.first_name,u.username FROM points p JOIN users u ON u.id=p.user_id WHERE p.group_id=? AND p.week=? ORDER BY p.points DESC,p.updated ASC LIMIT 1",(g,week)).fetchone()
        if not r:return None
        c.execute('INSERT INTO weekly_winners VALUES(NULL,?,?,?,?,?,?)',(g,week,r['user_id'],r['points'],prize,now())); return r
def previous_week():
    from datetime import date
    return wk(datetime.now(ZoneInfo(TIMEZONE))-timedelta(days=1))
