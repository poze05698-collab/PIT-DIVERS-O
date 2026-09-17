import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from config import DATABASE_PATH

def conn():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DATABASE_PATH, timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    return c

@contextmanager
def db():
    c=conn()
    try:
        yield c
        c.commit()
    finally:
        c.close()

def _columns(c, table):
    return {row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()}

def _add_column(c, table, column, definition):
    if column not in _columns(c, table):
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def migrate_db():
    """Only additive migrations. Existing data is preserved."""
    with db() as c:
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
            for column, definition in (("username","TEXT"),("first_name","TEXT"),("first_seen","TEXT"),("last_seen","TEXT"),("is_active","INTEGER DEFAULT 1")):
                _add_column(c,"users",column,definition)
            now_value=datetime.now(timezone.utc).isoformat()
            c.execute("UPDATE users SET first_seen=? WHERE first_seen IS NULL OR first_seen=''",(now_value,))
            c.execute("UPDATE users SET last_seen=? WHERE last_seen IS NULL OR last_seen=''",(now_value,))
            c.execute("UPDATE users SET is_active=1 WHERE is_active IS NULL")

        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'").fetchone():
            old_cols=_columns(c,"groups")
            for column,definition in (
                ("title","TEXT"),("username","TEXT"),("first_seen","TEXT"),("last_seen","TEXT"),
                ("enabled","INTEGER DEFAULT 1"),("morning","INTEGER DEFAULT 1"),("night","INTEGER DEFAULT 1"),
                ("prize","TEXT DEFAULT ''"),("start_time","TEXT DEFAULT '10:00'"),("end_time","TEXT DEFAULT '00:00'"),
                ("challenge_interval","INTEGER DEFAULT 25"),("challenge_points","INTEGER DEFAULT 10"),
                ("image_chance","INTEGER DEFAULT 35"),("morning_time","TEXT DEFAULT '08:00'"),("night_time","TEXT DEFAULT '22:00'"),
                ("prize1","TEXT DEFAULT ''"),("prize2","TEXT DEFAULT ''"),("prize3","TEXT DEFAULT ''"),
            ):
                _add_column(c,"groups",column,definition)
            if "entertainment_enabled" in old_cols: c.execute("UPDATE groups SET enabled=COALESCE(entertainment_enabled,1)")
            if "morning_enabled" in old_cols: c.execute("UPDATE groups SET morning=COALESCE(morning_enabled,1)")
            if "night_enabled" in old_cols: c.execute("UPDATE groups SET night=COALESCE(night_enabled,1)")
            if "weekly_prize" in old_cols: c.execute("UPDATE groups SET prize=COALESCE(weekly_prize,'')")
            # Preserve useful legacy values where possible; fill only missing/new settings.
            c.execute("UPDATE groups SET enabled=1 WHERE enabled IS NULL")
            c.execute("UPDATE groups SET morning=1 WHERE morning IS NULL")
            c.execute("UPDATE groups SET night=1 WHERE night IS NULL")
            c.execute("UPDATE groups SET prize='' WHERE prize IS NULL")
            c.execute("UPDATE groups SET start_time='10:00' WHERE start_time IS NULL OR start_time=''")
            c.execute("UPDATE groups SET end_time='00:00' WHERE end_time IS NULL OR end_time=''")
            c.execute("UPDATE groups SET challenge_interval=25 WHERE challenge_interval IS NULL OR challenge_interval<1")
            c.execute("UPDATE groups SET challenge_points=10 WHERE challenge_points IS NULL OR challenge_points<1")
            c.execute("UPDATE groups SET image_chance=35 WHERE image_chance IS NULL OR image_chance<0 OR image_chance>100")
            c.execute("UPDATE groups SET morning_time='08:00' WHERE morning_time IS NULL OR morning_time=''")
            c.execute("UPDATE groups SET night_time='22:00' WHERE night_time IS NULL OR night_time=''")

        # Migrate legacy challenges table safely. Older installations may only have
        # id/group_id/question. Add all fields used by the current challenge system
        # without deleting or replacing existing rows.
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='challenges'").fetchone():
            for column, definition in (
                ("answer", "TEXT"),
                ("category", "TEXT"),
                ("points", "INTEGER DEFAULT 1"),
                ("status", "TEXT DEFAULT 'answered'"),
                ("winner", "INTEGER"),
                ("created", "TEXT"),
                ("answered", "TEXT"),
                ("media_url", "TEXT"),
                ("media_title", "TEXT"),
                ("media_revealed", "INTEGER DEFAULT 0"),
                ("options_json", "TEXT"),
            ):
                _add_column(c, "challenges", column, definition)
            # Rows created by old versions are historical; do not leave them as
            # active challenges. New challenges explicitly receive status=active.
            c.execute("UPDATE challenges SET status='answered' WHERE status IS NULL OR status=''")
            c.execute("UPDATE challenges SET points=1 WHERE points IS NULL OR points<1")

        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='members'").fetchone():
            _add_column(c,"members","first_seen","TEXT")
            _add_column(c,"members","last_seen","TEXT")

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,first_seen TEXT,last_seen TEXT,is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY,title TEXT,username TEXT,first_seen TEXT,last_seen TEXT,enabled INTEGER DEFAULT 1,morning INTEGER DEFAULT 1,night INTEGER DEFAULT 1,prize TEXT DEFAULT '',start_time TEXT DEFAULT '10:00',end_time TEXT DEFAULT '00:00',challenge_interval INTEGER DEFAULT 25,challenge_points INTEGER DEFAULT 10,image_chance INTEGER DEFAULT 35,morning_time TEXT DEFAULT '08:00',night_time TEXT DEFAULT '22:00',prize1 TEXT DEFAULT '',prize2 TEXT DEFAULT '',prize3 TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS members(group_id INTEGER,user_id INTEGER,first_seen TEXT,last_seen TEXT,PRIMARY KEY(group_id,user_id));
        CREATE TABLE IF NOT EXISTS points(group_id INTEGER,user_id INTEGER,week TEXT,points INTEGER DEFAULT 0,updated TEXT,PRIMARY KEY(group_id,user_id,week));
        CREATE TABLE IF NOT EXISTS challenges(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,question TEXT,answer TEXT,category TEXT,points INTEGER,status TEXT DEFAULT 'active',winner INTEGER,created TEXT,answered TEXT,media_url TEXT,media_title TEXT,media_revealed INTEGER DEFAULT 0,options_json TEXT);
        CREATE TABLE IF NOT EXISTS follows(follower INTEGER,followed INTEGER,created TEXT,PRIMARY KEY(follower,followed));
        CREATE TABLE IF NOT EXISTS reactions(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,user_id INTEGER,kind TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,user_id INTEGER,text TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS giveaways(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,prize TEXT,status TEXT DEFAULT 'open',winner INTEGER,created TEXT);
        CREATE TABLE IF NOT EXISTS giveaway_entries(giveaway_id INTEGER,user_id INTEGER,created TEXT,PRIMARY KEY(giveaway_id,user_id));
        CREATE TABLE IF NOT EXISTS weekly_winners(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,week TEXT,user_id INTEGER,points INTEGER,prize TEXT,closed TEXT,UNIQUE(group_id,week));
        """)
    migrate_db()
    from database.features import init_features
    init_features()
