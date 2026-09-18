import random, json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from config import TIMEZONE
from database.connection import db
from database.points import wk, previous_week

VICTORY = [
    '🔥 Boa demais!', '🧠 Resposta certeira!', '🎯 Na mosca!',
    '⚡ Foi rápido demais!', '🏆 Ponto garantido!', '🚀 Que velocidade!',
    '👏 Brilhou nessa!', '💥 Acertou em cheio!', '🥳 Essa foi sua!',
    '👑 O mestre atacou novamente!', '🐶 O PITBULL aprovou!', '🔥 Que acerto absurdo!'
]

def now(): return datetime.now(timezone.utc).isoformat()

def local_day(): return datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()

def init_features():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS feature_settings(group_id INTEGER PRIMARY KEY,
          xp_enabled INTEGER DEFAULT 1, combo_enabled INTEGER DEFAULT 1, achievements_enabled INTEGER DEFAULT 1,
          missions_enabled INTEGER DEFAULT 1, chest_enabled INTEGER DEFAULT 1, battles_enabled INTEGER DEFAULT 1,
          memory_enabled INTEGER DEFAULT 1, events_enabled INTEGER DEFAULT 1, category_rank_enabled INTEGER DEFAULT 1,
          social_enabled INTEGER DEFAULT 1, victory_messages_enabled INTEGER DEFAULT 1,
          xp_per_answer INTEGER DEFAULT 5, combo_bonus INTEGER DEFAULT 2, chest_points INTEGER DEFAULT 10,
          mission_target INTEGER DEFAULT 5, battle_points INTEGER DEFAULT 15, event_multiplier INTEGER DEFAULT 2,
          howto_enabled INTEGER DEFAULT 1, howto_text TEXT DEFAULT '', chest_duration_minutes INTEGER DEFAULT 10) ;
        CREATE TABLE IF NOT EXISTS xp_levels(group_id INTEGER,user_id INTEGER,level INTEGER DEFAULT 1,xp INTEGER DEFAULT 0,updated TEXT,
          PRIMARY KEY(group_id,user_id));
        CREATE TABLE IF NOT EXISTS combos(group_id INTEGER,user_id INTEGER,streak INTEGER DEFAULT 0,best INTEGER DEFAULT 0,updated TEXT,
          PRIMARY KEY(group_id,user_id));
        CREATE TABLE IF NOT EXISTS achievements(group_id INTEGER,user_id INTEGER,badge TEXT,created TEXT,
          PRIMARY KEY(group_id,user_id,badge));
        CREATE TABLE IF NOT EXISTS missions(group_id INTEGER,user_id INTEGER,day TEXT,progress INTEGER DEFAULT 0,target INTEGER DEFAULT 5,claimed INTEGER DEFAULT 0,
          PRIMARY KEY(group_id,user_id,day));
        CREATE TABLE IF NOT EXISTS chests(group_id INTEGER,user_id INTEGER,day TEXT,points INTEGER DEFAULT 0,claimed INTEGER DEFAULT 0,
          PRIMARY KEY(group_id,user_id,day));
        CREATE TABLE IF NOT EXISTS battles(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,challenger INTEGER,opponent INTEGER,status TEXT DEFAULT 'pending',winner INTEGER,created TEXT,points INTEGER DEFAULT 15);
        CREATE TABLE IF NOT EXISTS memory_games(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,question TEXT,answer TEXT,status TEXT DEFAULT 'active',winner INTEGER,created TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,type TEXT,ends TEXT,multiplier INTEGER DEFAULT 2,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS weekly_seasons(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,week TEXT,closed TEXT,
          winner1 INTEGER,points1 INTEGER,prize1 TEXT,winner2 INTEGER,points2 INTEGER,prize2 TEXT,winner3 INTEGER,points3 INTEGER,prize3 TEXT,
          UNIQUE(group_id,week));
        CREATE TABLE IF NOT EXISTS anti_spam(group_id INTEGER,user_id INTEGER,minute TEXT,actions INTEGER DEFAULT 0,
          PRIMARY KEY(group_id,user_id,minute));
        ''')
        cols={r[1] for r in c.execute('PRAGMA table_info(battles)').fetchall()}
        for column, definition in (("question","TEXT"),("answer","TEXT"),("options_json","TEXT"),("answered","TEXT")):
            if column not in cols: c.execute(f'ALTER TABLE battles ADD COLUMN {column} {definition}')
        cols={r[1] for r in c.execute('PRAGMA table_info(feature_settings)').fetchall()}
        if 'chest_duration_minutes' not in cols:
            c.execute('ALTER TABLE feature_settings ADD COLUMN chest_duration_minutes INTEGER DEFAULT 10')
        c.execute('UPDATE feature_settings SET chest_duration_minutes=10 WHERE chest_duration_minutes IS NULL OR chest_duration_minutes<1 OR chest_duration_minutes>1440')

def ensure_group(gid):
    with db() as c:
        c.execute('INSERT OR IGNORE INTO feature_settings(group_id,howto_text) VALUES(?,?)',(gid,''))

def settings(gid):
    ensure_group(gid)
    with db() as c: return c.execute('SELECT * FROM feature_settings WHERE group_id=?',(gid,)).fetchone()

def toggle(gid, field):
    ensure_group(gid)
    allowed={'xp_enabled','combo_enabled','achievements_enabled','missions_enabled','chest_enabled','battles_enabled','memory_enabled','events_enabled','category_rank_enabled','social_enabled','victory_messages_enabled','howto_enabled'}
    if field not in allowed: raise ValueError(field)
    with db() as c:
        r=c.execute(f'SELECT {field} v FROM feature_settings WHERE group_id=?',(gid,)).fetchone(); v=0 if r['v'] else 1
        c.execute(f'UPDATE feature_settings SET {field}=? WHERE group_id=?',(v,gid)); return bool(v)

def set_value(gid, field, value):
    ensure_group(gid)
    allowed={'xp_per_answer','combo_bonus','chest_points','mission_target','battle_points','event_multiplier','chest_duration_minutes','howto_text'}
    if field not in allowed: raise ValueError(field)
    with db() as c: c.execute(f'UPDATE feature_settings SET {field}=? WHERE group_id=?',(value,gid))

def award(gid, uid, base_points, category='Geral'):
    s=settings(gid); out={'xp':0,'level':1,'combo':0,'new_badges':[],'bonus':0}
    if s['xp_enabled']:
        xp=max(1,int(s['xp_per_answer']))
        with db() as c:
            r=c.execute('SELECT level,xp FROM xp_levels WHERE group_id=? AND user_id=?',(gid,uid)).fetchone()
            level,xp0=(r['level'],r['xp']) if r else (1,0); xp0 += xp
            while xp0 >= level*100:
                xp0 -= level*100; level += 1
            c.execute('INSERT INTO xp_levels VALUES(?,?,?,?,?) ON CONFLICT(group_id,user_id) DO UPDATE SET level=excluded.level,xp=excluded.xp,updated=excluded.updated',(gid,uid,level,xp0,now()))
            out['xp']=xp; out['level']=level
    if s['combo_enabled']:
        with db() as c:
            r=c.execute('SELECT streak,best FROM combos WHERE group_id=? AND user_id=?',(gid,uid)).fetchone()
            streak=(r['streak'] if r else 0)+1; best=max(streak,r['best'] if r else 0)
            c.execute('INSERT INTO combos VALUES(?,?,?,?,?) ON CONFLICT(group_id,user_id) DO UPDATE SET streak=excluded.streak,best=excluded.best,updated=excluded.updated',(gid,uid,streak,best,now()))
            out['combo']=streak
            if streak >= 3: out['bonus']=int(s['combo_bonus'])*(streak-2)
    if s['achievements_enabled']:
        checks=[]
        total_week=0
        with db() as c:
            r=c.execute('SELECT points FROM points WHERE group_id=? AND user_id=? AND week=?',(gid,uid,wk())).fetchone(); total_week=r['points'] if r else 0
            if total_week >= 50: checks.append('50 pontos')
            if total_week >= 100: checks.append('100 pontos')
            if out['combo'] >= 5: checks.append('Combo 5')
            if out['combo'] >= 10: checks.append('Combo 10')
            for badge in checks:
                if not c.execute('SELECT 1 FROM achievements WHERE group_id=? AND user_id=? AND badge=?',(gid,uid,badge)).fetchone():
                    c.execute('INSERT INTO achievements VALUES(?,?,?,?)',(gid,uid,badge,now())); out['new_badges'].append(badge)
    mult=current_multiplier(gid) if s['events_enabled'] else 1
    if mult > 1:
        out['bonus'] += max(0, int(base_points) * (mult - 1))
    if s['missions_enabled']:
        day=local_day()
        with db() as c:
            c.execute('INSERT INTO missions(group_id,user_id,day,progress,target,claimed) VALUES(?,?,?,?,?,0) ON CONFLICT(group_id,user_id,day) DO UPDATE SET progress=MIN(progress+1,target)',(gid,uid,day,1,int(s['mission_target'])))
    return out

def daily_status(gid,uid):
    s=settings(gid); day=local_day()
    with db() as c:
        m=c.execute('SELECT * FROM missions WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)).fetchone()
        ch=c.execute('SELECT * FROM chests WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)).fetchone()
    return m,ch

def release_chest(gid, minutes):
    s=settings(gid)
    if not s['chest_enabled']:
        return None
    minutes=max(1,min(1440,int(minutes)))
    started=datetime.now(timezone.utc)
    ends=started.replace(microsecond=0) + __import__('datetime').timedelta(minutes=minutes)
    with db() as c:
        c.execute('UPDATE chest_rounds SET active=0 WHERE group_id=? AND active=1',(gid,))
        cur=c.execute('INSERT INTO chest_rounds(group_id,started,ends,active) VALUES(?,?,?,1)',(gid,started.isoformat(),ends.isoformat()))
        return cur.lastrowid, ends.isoformat()

def chest_open(gid):
    with db() as c:
        r=c.execute('SELECT * FROM chest_rounds WHERE group_id=? AND active=1 ORDER BY id DESC LIMIT 1',(gid,)).fetchone()
        if not r: return None
        if r['ends'] <= now():
            c.execute('UPDATE chest_rounds SET active=0 WHERE id=?',(r['id'],)); return None
        return r

def claim_chest(gid,uid):
    s=settings(gid)
    if not s['chest_enabled']: return None
    if not chest_open(gid): return None
    day=local_day()
    with db() as c:
        r=c.execute('SELECT claimed FROM chests WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)).fetchone()
        if r and r['claimed']: return None
        pts=max(1,int(s['chest_points'])); c.execute('INSERT INTO chests VALUES(?,?,?,?,1) ON CONFLICT(group_id,user_id,day) DO UPDATE SET claimed=1,points=excluded.points',(gid,uid,day,pts)); return pts

def claim_mission(gid,uid):
    s=settings(gid); day=local_day()
    with db() as c:
        r=c.execute('SELECT progress,target,claimed FROM missions WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)).fetchone()
        if not r or r['claimed'] or r['progress'] < r['target']: return None
        pts=max(1,int(s['mission_target'])*2); c.execute('UPDATE missions SET claimed=1 WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)); return pts

def create_battle(gid, challenger, opponent, points, question, answer, options):
    with db() as c:
        cur=c.execute('INSERT INTO battles(group_id,challenger,opponent,status,created,points,question,answer,options_json) VALUES(?,?,?,?,?,?,?,?,?)',(gid,challenger,opponent,'pending',now(),points,question,answer,json.dumps(options,ensure_ascii=False)))
        return cur.lastrowid

def get_battle(bid):
    with db() as c: return c.execute('SELECT * FROM battles WHERE id=?',(bid,)).fetchone()

def finish_battle(bid, winner):
    with db() as c:
        cur=c.execute("UPDATE battles SET status='finished',winner=?,answered=? WHERE id=? AND status='active'",(winner,now(),bid))
        return cur.rowcount == 1

def current_multiplier(gid):
    with db() as c:
        r=c.execute('SELECT multiplier FROM events WHERE group_id=? AND active=1 AND ends>? ORDER BY id DESC LIMIT 1',(gid,now())).fetchone()
        return int(r['multiplier']) if r else 1

def reset_combo(gid,uid):
    with db() as c:
        c.execute('UPDATE combos SET streak=0,updated=? WHERE group_id=? AND user_id=?',(now(),gid,uid))

def victory(gid,kind='first'):
    s=settings(gid)
    if not s['victory_messages_enabled']: return '🎉 Acertou!'
    return random.choice(VICTORY)

def category_rank(gid, category, limit=10):
    with db() as c:
        return c.execute('''SELECT c.winner user_id,SUM(c.points) points,u.first_name,u.username FROM challenges c JOIN users u ON u.id=c.winner WHERE c.group_id=? AND c.category=? AND c.status='answered' GROUP BY c.winner ORDER BY points DESC LIMIT ?''',(gid,category,limit)).fetchall()

def top3(gid, week=None):
    week=week or wk()
    with db() as c:
        return c.execute('''SELECT p.user_id,p.points,u.first_name,u.username FROM points p JOIN users u ON u.id=p.user_id WHERE p.group_id=? AND p.week=? ORDER BY p.points DESC,p.updated ASC LIMIT 3''',(gid,week)).fetchall()

def close_season(gid, week, prizes):
    with db() as c:
        if c.execute('SELECT 1 FROM weekly_seasons WHERE group_id=? AND week=?',(gid,week)).fetchone(): return []
        rows=c.execute('''SELECT p.user_id,p.points,u.first_name,u.username FROM points p JOIN users u ON u.id=p.user_id WHERE p.group_id=? AND p.week=? ORDER BY p.points DESC,p.updated ASC LIMIT 3''',(gid,week)).fetchall()
        vals=[]
        for i in range(3):
            r=rows[i] if i<len(rows) else None; vals.extend([r['user_id'] if r else None,r['points'] if r else 0,prizes[i] if i<len(prizes) else ''])
        c.execute('INSERT INTO weekly_seasons(group_id,week,closed,winner1,points1,prize1,winner2,points2,prize2,winner3,points3,prize3) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(gid,week,now(),*vals))
        return rows

def season_history(gid,limit=5):
    with db() as c:return c.execute('SELECT * FROM weekly_seasons WHERE group_id=? ORDER BY id DESC LIMIT ?',(gid,limit)).fetchall()

def spam_ok(gid,uid):
    minute=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M')
    with db() as c:
        r=c.execute('SELECT actions FROM anti_spam WHERE group_id=? AND user_id=? AND minute=?',(gid,uid,minute)).fetchone(); n=(r['actions'] if r else 0)+1
        c.execute('INSERT INTO anti_spam VALUES(?,?,?,?) ON CONFLICT(group_id,user_id,minute) DO UPDATE SET actions=excluded.actions',(gid,uid,minute,n)); return n<=12
