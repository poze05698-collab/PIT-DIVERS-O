import random, json
from datetime import datetime, timezone
from database.connection import db
from database.points import wk, previous_week

VICTORY = [
    '🔥 Boa demais!', '🧠 Resposta certeira!', '🎯 Na mosca!',
    '⚡ Foi rápido demais!', '🏆 Ponto garantido!', '🚀 Que velocidade!',
    '👏 Brilhou nessa!', '💥 Acertou em cheio!', '🥳 Essa foi sua!',
    '👑 O mestre atacou novamente!', '🐶 O PITBULL aprovou!', '🔥 Que acerto absurdo!'
]

def now(): return datetime.now(timezone.utc).isoformat()

def init_features():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS feature_settings(group_id INTEGER PRIMARY KEY,
          xp_enabled INTEGER DEFAULT 1, combo_enabled INTEGER DEFAULT 1, achievements_enabled INTEGER DEFAULT 1,
          missions_enabled INTEGER DEFAULT 1, chest_enabled INTEGER DEFAULT 1, battles_enabled INTEGER DEFAULT 1,
          memory_enabled INTEGER DEFAULT 1, events_enabled INTEGER DEFAULT 1, category_rank_enabled INTEGER DEFAULT 1,
          social_enabled INTEGER DEFAULT 1, victory_messages_enabled INTEGER DEFAULT 1,
          xp_per_answer INTEGER DEFAULT 5, combo_bonus INTEGER DEFAULT 2, chest_points INTEGER DEFAULT 10,
          mission_target INTEGER DEFAULT 5, battle_points INTEGER DEFAULT 15, event_multiplier INTEGER DEFAULT 2, mission_reward INTEGER DEFAULT 10,
          howto_enabled INTEGER DEFAULT 1, chest_duration_minutes INTEGER DEFAULT 10, chest_active_until TEXT DEFAULT '', howto_text TEXT DEFAULT '') ;
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
        -- Novo sistema de 3 baús por dia. A tabela antiga 'chests' é preservada
        -- para não perder dados; os novos resgates usam um ID por liberação.
        CREATE TABLE IF NOT EXISTS chest_releases(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          group_id INTEGER NOT NULL,
          day TEXT NOT NULL,
          points INTEGER NOT NULL DEFAULT 10,
          active_until TEXT NOT NULL,
          created TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1,
          message_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS chest_claims(
          release_id INTEGER NOT NULL,
          group_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          points INTEGER NOT NULL,
          claimed TEXT NOT NULL,
          PRIMARY KEY(release_id,user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_chest_releases_group_day ON chest_releases(group_id,day);
        CREATE TABLE IF NOT EXISTS battles(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,challenger INTEGER,opponent INTEGER,status TEXT DEFAULT 'pending',winner INTEGER,created TEXT,points INTEGER DEFAULT 15);
        CREATE TABLE IF NOT EXISTS memory_games(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,question TEXT,answer TEXT,status TEXT DEFAULT 'active',winner INTEGER,created TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,type TEXT,ends TEXT,multiplier INTEGER DEFAULT 2,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS weekly_seasons(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,week TEXT,closed TEXT,
          winner1 INTEGER,points1 INTEGER,prize1 TEXT,winner2 INTEGER,points2 INTEGER,prize2 TEXT,winner3 INTEGER,points3 INTEGER,prize3 TEXT,
          UNIQUE(group_id,week));
        CREATE TABLE IF NOT EXISTS anti_spam(group_id INTEGER,user_id INTEGER,minute TEXT,actions INTEGER DEFAULT 0,
          PRIMARY KEY(group_id,user_id,minute));
        ''')
        # Battle fields were introduced after the original battle table.
        # Add them in-place so existing battles/history remain untouched.
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='battles'").fetchone():
            for column, definition in (("question","TEXT"),("answer","TEXT"),("options_json","TEXT"),("message_id","INTEGER")):
                if column not in {r[1] for r in c.execute('PRAGMA table_info(battles)').fetchall()}:
                    c.execute(f"ALTER TABLE battles ADD COLUMN {column} {definition}")

        cols={r[1] for r in c.execute('PRAGMA table_info(feature_settings)').fetchall()}
        if 'mission_reward' not in cols: c.execute("ALTER TABLE feature_settings ADD COLUMN mission_reward INTEGER DEFAULT 10")
        if 'chest_duration_minutes' not in cols: c.execute("ALTER TABLE feature_settings ADD COLUMN chest_duration_minutes INTEGER DEFAULT 10")
        if 'chest_active_until' not in cols: c.execute("ALTER TABLE feature_settings ADD COLUMN chest_active_until TEXT DEFAULT ''")
        chest_cols={r[1] for r in c.execute('PRAGMA table_info(chest_releases)').fetchall()}
        if 'message_id' not in chest_cols: c.execute("ALTER TABLE chest_releases ADD COLUMN message_id INTEGER")

def ensure_group(gid):
    with db() as c:
        c.execute('INSERT OR IGNORE INTO feature_settings(group_id,howto_text) VALUES(?,?)',(gid,''))

def settings(gid):
    ensure_group(gid)
    with db() as c: return c.execute('SELECT * FROM feature_settings WHERE group_id=?',(gid,)).fetchone()

def toggle(gid, field):
    ensure_group(gid)
    allowed={'xp_enabled','combo_enabled','achievements_enabled','missions_enabled','chest_enabled','memory_enabled','events_enabled','category_rank_enabled','social_enabled','victory_messages_enabled','howto_enabled'}
    if field not in allowed: raise ValueError(field)
    with db() as c:
        r=c.execute(f'SELECT {field} v FROM feature_settings WHERE group_id=?',(gid,)).fetchone(); v=0 if r['v'] else 1
        c.execute(f'UPDATE feature_settings SET {field}=? WHERE group_id=?',(v,gid)); return bool(v)

def set_value(gid, field, value):
    ensure_group(gid)
    allowed={'xp_per_answer','combo_bonus','chest_points','mission_target','mission_reward','event_multiplier','chest_duration_minutes','howto_text'}
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
        day=_local_day()
        with db() as c:
            c.execute('INSERT INTO missions(group_id,user_id,day,progress,target,claimed) VALUES(?,?,?,?,?,0) ON CONFLICT(group_id,user_id,day) DO UPDATE SET progress=MIN(progress+1,target)',(gid,uid,day,1,int(s['mission_target'])))
    return out

def _local_day():
    """Dia civil do fuso configurado do bot, sem alterar dados históricos."""
    try:
        from config import TIMEZONE
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()

def daily_status(gid,uid):
    day=_local_day()
    with db() as c:
        m=c.execute('SELECT * FROM missions WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)).fetchone()
        # Retorna também o último baú legado para compatibilidade com versões antigas.
        ch=c.execute('SELECT * FROM chests WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)).fetchone()
    return m,ch

def chest_daily_count(gid):
    day=_local_day()
    with db() as c:
        c.execute('UPDATE chest_releases SET active=0 WHERE group_id=? AND day=? AND active=1 AND active_until<=?',(gid,day,now()))
        r=c.execute('SELECT COUNT(*) n FROM chest_releases WHERE group_id=? AND day=?',(gid,day)).fetchone()
        return int(r['n'] or 0)

def release_chest(gid, minutes=None):
    """Libera um dos 3 baús diários; cada membro pode resgatar uma vez por liberação."""
    s=settings(gid)
    if not s['chest_enabled']:
        return None, 'disabled'
    try:
        minutes=max(1,min(1440,int(minutes if minutes is not None else s['chest_duration_minutes'] or 10)))
    except Exception:
        minutes=10
    day=_local_day()
    from datetime import timedelta
    created=now()
    until=(datetime.now(timezone.utc)+timedelta(minutes=minutes)).isoformat()
    pts=max(1,int(s['chest_points'] or 1))
    with db() as c:
        # Fecha liberações expiradas antes de contar.
        c.execute('UPDATE chest_releases SET active=0 WHERE group_id=? AND day=? AND active=1 AND active_until<=?',(gid,day,created))
        count=int(c.execute('SELECT COUNT(*) n FROM chest_releases WHERE group_id=? AND day=?',(gid,day)).fetchone()['n'] or 0)
        if count>=3:
            return None, 'limit'
        # Evita dois baús simultaneamente; o admin libera o próximo após o anterior expirar.
        active=c.execute('SELECT id FROM chest_releases WHERE group_id=? AND day=? AND active=1 AND active_until>? LIMIT 1',(gid,day,created)).fetchone()
        if active:
            return None, 'active'
        cur=c.execute('INSERT INTO chest_releases(group_id,day,points,active_until,created,active,message_id) VALUES(?,?,?,?,?,1,NULL)',(gid,day,pts,until,created))
        rid=cur.lastrowid
        return {'id':rid,'group_id':gid,'day':day,'points':pts,'minutes':minutes,'active_until':until,'number':count+1}, None

def chest_release_status(gid):
    day=_local_day()
    with db() as c:
        c.execute('UPDATE chest_releases SET active=0 WHERE group_id=? AND day=? AND active=1 AND active_until<=?',(gid,day,now()))
        r=c.execute('SELECT COUNT(*) n FROM chest_releases WHERE group_id=? AND day=?',(gid,day)).fetchone()
        active=c.execute('SELECT * FROM chest_releases WHERE group_id=? AND day=? AND active=1 ORDER BY id DESC LIMIT 1',(gid,day)).fetchone()
    return int(r['n'] or 0), active

def claim_chest_release(release_id, gid, uid):
    """Resgate atômico: um usuário só recebe uma vez naquele baú."""
    with db() as c:
        r=c.execute('SELECT * FROM chest_releases WHERE id=? AND group_id=? AND active=1',(release_id,gid)).fetchone()
        if not r:
            return None
        if str(r['active_until']) <= now():
            c.execute('UPDATE chest_releases SET active=0 WHERE id=? AND active=1',(release_id,))
            return None
        pts=max(1,int(r['points']))
        cur=c.execute('INSERT OR IGNORE INTO chest_claims(release_id,group_id,user_id,points,claimed) VALUES(?,?,?,?,?)',(release_id,gid,uid,pts,now()))
        if cur.rowcount != 1:
            return None
        return pts

def set_chest_message_id(release_id, message_id):
    with db() as c:
        c.execute('UPDATE chest_releases SET message_id=? WHERE id=?',(int(message_id),int(release_id)))

def expire_chests():
    current=now()
    with db() as c:
        rows=c.execute('SELECT id,group_id,message_id FROM chest_releases WHERE active=1 AND active_until<=?',(current,)).fetchall()
        if rows:
            c.execute('UPDATE chest_releases SET active=0 WHERE active=1 AND active_until<=?',(current,))
        return [(int(r['id']),int(r['group_id']),int(r['message_id'])) for r in rows if r['message_id']]

def deactivate_expired_chests():
    expire_chests()

def claim_mission(gid,uid):
    s=settings(gid); day=_local_day()
    with db() as c:
        r=c.execute('SELECT progress,target,claimed FROM missions WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)).fetchone()
        if not r or r['claimed'] or r['progress'] < r['target']: return None
        pts=max(1,int(s['mission_reward'])); c.execute('UPDATE missions SET claimed=1 WHERE group_id=? AND user_id=? AND day=?',(gid,uid,day)); return pts

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
