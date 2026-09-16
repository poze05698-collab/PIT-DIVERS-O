from datetime import datetime,timezone
from database.connection import db
def now(): return datetime.now(timezone.utc).isoformat()
def upsert(u):
    with db() as c: c.execute("INSERT INTO users VALUES(?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name,last_seen=excluded.last_seen,is_active=1",(u.id,u.username,u.first_name or 'Usuário',now(),now()))
def get(uid):
    with db() as c:return c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
