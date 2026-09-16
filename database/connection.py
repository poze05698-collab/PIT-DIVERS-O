import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH
def conn():
    c=sqlite3.connect(DATABASE_PATH,timeout=30); c.row_factory=sqlite3.Row; c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA busy_timeout=30000'); return c
@contextmanager
def db():
    c=conn()
    try: yield c; c.commit()
    finally: c.close()
def init_db():
    with db() as c: c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,first_seen TEXT,last_seen TEXT,is_active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY,title TEXT,username TEXT,first_seen TEXT,last_seen TEXT,enabled INTEGER DEFAULT 1,morning INTEGER DEFAULT 1,night INTEGER DEFAULT 1,prize TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS members(group_id INTEGER,user_id INTEGER,first_seen TEXT,last_seen TEXT,PRIMARY KEY(group_id,user_id));
    CREATE TABLE IF NOT EXISTS points(group_id INTEGER,user_id INTEGER,week TEXT,points INTEGER DEFAULT 0,updated TEXT,PRIMARY KEY(group_id,user_id,week));
    CREATE TABLE IF NOT EXISTS challenges(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,question TEXT,answer TEXT,category TEXT,points INTEGER,status TEXT DEFAULT 'active',winner INTEGER,created TEXT,answered TEXT);
    CREATE TABLE IF NOT EXISTS follows(follower INTEGER,followed INTEGER,created TEXT,PRIMARY KEY(follower,followed));
    CREATE TABLE IF NOT EXISTS reactions(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,user_id INTEGER,kind TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,user_id INTEGER,text TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS giveaways(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,prize TEXT,status TEXT DEFAULT 'open',winner INTEGER,created TEXT);
    CREATE TABLE IF NOT EXISTS giveaway_entries(giveaway_id INTEGER,user_id INTEGER,created TEXT,PRIMARY KEY(giveaway_id,user_id));
    CREATE TABLE IF NOT EXISTS weekly_winners(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,week TEXT,user_id INTEGER,points INTEGER,prize TEXT,closed TEXT,UNIQUE(group_id,week));
    """)
