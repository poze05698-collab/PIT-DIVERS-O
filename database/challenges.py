from datetime import datetime,timezone
from database.connection import db
def now():return datetime.now(timezone.utc).isoformat()
def active(g):
    with db() as c:return c.execute("SELECT * FROM challenges WHERE group_id=? AND status='active' ORDER BY id DESC LIMIT 1",(g,)).fetchone()
def create(g,q,a,cat,pts):
    with db() as c:
        c.execute("UPDATE challenges SET status='cancelled' WHERE group_id=? AND status='active'",(g,)); r=c.execute("INSERT INTO challenges(group_id,question,answer,category,points,status,created) VALUES(?,?,?,?,?,'active',?)",(g,q,a,cat,pts,now())); return r.lastrowid
def win(cid,uid):
    with db() as c:
        r=c.execute("SELECT * FROM challenges WHERE id=? AND status='active'",(cid,)).fetchone()
        if not r:return None
        c.execute("UPDATE challenges SET status='answered',winner=?,answered=? WHERE id=? AND status='active'",(uid,now(),cid)); return r if c.execute('SELECT changes()').fetchone()[0] else None
def cancel(g):
    with db() as c:c.execute("UPDATE challenges SET status='cancelled' WHERE group_id=? AND status='active'",(g,))
