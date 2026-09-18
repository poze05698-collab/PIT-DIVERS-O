from datetime import datetime,timezone
from database.connection import db
def now():return datetime.now(timezone.utc).isoformat()
def follow(a,b):
    if a==b:return False
    with db() as c:
        try:c.execute('INSERT INTO follows VALUES(?,?,?)',(a,b,now()));return True
        except:return False
def unfollow(a,b):
    with db() as c:return c.execute('DELETE FROM follows WHERE follower=? AND followed=?',(a,b)).rowcount>0
def counts(u):
    with db() as c:return (c.execute('SELECT COUNT(*) n FROM follows WHERE followed=?',(u,)).fetchone()['n'],c.execute('SELECT COUNT(*) n FROM follows WHERE follower=?',(u,)).fetchone()['n'])
def feedback(g,u,t):
    with db() as c:c.execute('INSERT INTO feedback(group_id,user_id,text,created) VALUES(?,?,?,?)',(g,u,t,now()))
def reaction(g,u,k):
    with db() as c:c.execute('INSERT INTO reactions(group_id,user_id,kind,created) VALUES(?,?,?,?)',(g,u,k,now()))
