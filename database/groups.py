from datetime import datetime,timezone
from database.connection import db
def now(): return datetime.now(timezone.utc).isoformat()
def upsert(chat):
    with db() as c:c.execute("INSERT INTO groups VALUES(?,?,?,?,?,1,1,1,'') ON CONFLICT(id) DO UPDATE SET title=excluded.title,username=excluded.username,last_seen=excluded.last_seen",(chat.id,chat.title or 'Grupo',getattr(chat,'username',None),now(),now()))
def member(g,u):
    with db() as c:c.execute("INSERT INTO members VALUES(?,?,?,?) ON CONFLICT(group_id,user_id) DO UPDATE SET last_seen=excluded.last_seen",(g,u,now(),now()))
def get(g):
    with db() as c:return c.execute('SELECT * FROM groups WHERE id=?',(g,)).fetchone()
def all_groups():
    with db() as c:return c.execute('SELECT * FROM groups').fetchall()
def enabled(g):
    r=get(g); return bool(r and r['enabled'])
def toggle(g,v):
    with db() as c:c.execute('UPDATE groups SET enabled=? WHERE id=?',(int(v),g))
def setting(g,col,v):
    if col not in {'morning','night'}: raise ValueError(col)
    with db() as c:c.execute(f'UPDATE groups SET {col}=? WHERE id=?',(int(v),g))
def prize(g,text):
    with db() as c:c.execute('UPDATE groups SET prize=? WHERE id=?',(text,g))
