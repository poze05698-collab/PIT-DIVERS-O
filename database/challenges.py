from datetime import datetime, timezone, timedelta
from database.connection import db

def now(): return datetime.now(timezone.utc).isoformat()

def active(g):
    with db() as c:
        return c.execute("SELECT * FROM challenges WHERE group_id=? AND status='active' ORDER BY id DESC LIMIT 1",(g,)).fetchone()

def create(g,q,a,cat,pts,media_url=None,media_title=None,options_json=None,expires_minutes=30):
    created=now()
    try:
        expires=(datetime.now(timezone.utc)+timedelta(minutes=max(1,int(expires_minutes)))).isoformat()
    except Exception:
        expires=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()
    with db() as c:
        c.execute("UPDATE challenges SET status='cancelled' WHERE group_id=? AND status='active'",(g,))
        r=c.execute("INSERT INTO challenges(group_id,question,answer,category,points,status,created,media_url,media_title,media_revealed,options_json,message_id,expires) VALUES(?,?,?,?,?,'active',?,?,?,?,?,?,?)",(g,q,a,cat,pts,created,media_url,media_title,0,options_json,None,expires))
        return r.lastrowid

def set_message_id(cid,message_id):
    with db() as c: c.execute('UPDATE challenges SET message_id=? WHERE id=?',(message_id,cid))

def win(cid,uid):
    with db() as c:
        r=c.execute("SELECT * FROM challenges WHERE id=? AND status='active'",(cid,)).fetchone()
        if not r: return None
        cur=c.execute("UPDATE challenges SET status='answered',winner=?,answered=? WHERE id=? AND status='active'",(uid,now(),cid))
        return r if cur.rowcount==1 else None

def cancel(g):
    with db() as c:
        r=c.execute("SELECT * FROM challenges WHERE group_id=? AND status='active' ORDER BY id DESC LIMIT 1",(g,)).fetchone()
        if not r: return None
        c.execute("UPDATE challenges SET status='cancelled' WHERE id=? AND status='active'",(r['id'],))
        return r


def expired(g=None):
    current=now()
    with db() as c:
        if g is None:
            rows=c.execute("SELECT * FROM challenges WHERE status='active' AND expires IS NOT NULL AND expires<=?",(current,)).fetchall()
        else:
            rows=c.execute("SELECT * FROM challenges WHERE group_id=? AND status='active' AND expires IS NOT NULL AND expires<=?",(g,current)).fetchall()
        for r in rows:
            c.execute("UPDATE challenges SET status='expired' WHERE id=? AND status='active'",(r['id'],))
        return rows
