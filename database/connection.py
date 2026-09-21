import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from contextlib import contextmanager
from pathlib import Path
from config import DATABASE_PATH, TIMEZONE

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
                ("message_id", "INTEGER"),
                ("expires", "TEXT"),
            ):
                _add_column(c, "challenges", column, definition)
            # Rows created by old versions are historical; do not leave them as
            # active challenges. New challenges explicitly receive status=active.
            c.execute("UPDATE challenges SET status='answered' WHERE status IS NULL OR status=''")
            # Desafios de versões antigas não possuem `expires`. Nunca deixe um
            # registro legado sem prazo bloquear o grupo indefinidamente.
            c.execute("UPDATE challenges SET status='answered' WHERE status='active' AND expires IS NULL")
            c.execute("UPDATE challenges SET points=1 WHERE points IS NULL OR points<1")

        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='members'").fetchone():
            _add_column(c,"members","first_seen","TEXT")
            _add_column(c,"members","last_seen","TEXT")

        # Controle de temporada manual. Nunca muda automaticamente com a virada
        # do calendário; a nova temporada só é aberta pelo painel Admin.
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='season_control'").fetchone():
            groups = c.execute("SELECT id FROM groups").fetchall() if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'").fetchone() else []
            for g in groups:
                gid = int(g["id"])
                exists = c.execute("SELECT 1 FROM season_control WHERE group_id=?", (gid,)).fetchone()
                if exists:
                    continue
                latest = c.execute(
                    "SELECT p.week FROM points p "
                    "WHERE p.group_id=? AND NOT EXISTS "
                    "(SELECT 1 FROM weekly_seasons s WHERE s.group_id=p.group_id AND s.week=p.week) "
                    "ORDER BY p.updated DESC LIMIT 1",
                    (gid,)
                ).fetchone()
                active_week = latest["week"] if latest else (lambda d: f"{d.isocalendar().year}-W{d.isocalendar().week:02d}")(datetime.now(ZoneInfo(TIMEZONE)).date())
                c.execute(
                    "INSERT INTO season_control(group_id,active_week,opened,closed_count,status) VALUES(?,?,?,0,'active')",
                    (gid, active_week, datetime.now(timezone.utc).isoformat())
                )
            _add_column(c, "season_control", "status", "TEXT NOT NULL DEFAULT 'active'")
            c.execute("UPDATE season_control SET status='active' WHERE status IS NULL OR status=''")

        # Cria um registro inicial de auditoria para saldos já existentes.
        # Não altera nenhum ponto; apenas documenta o saldo legado.
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='points_ledger'").fetchone():
            rows = c.execute("SELECT group_id,user_id,week,points,updated FROM points").fetchall()
            for r in rows:
                if not c.execute(
                    "SELECT 1 FROM points_ledger WHERE group_id=? AND user_id=? AND week=? LIMIT 1",
                    (r["group_id"], r["user_id"], r["week"])
                ).fetchone():
                    c.execute(
                        "INSERT INTO points_ledger(group_id,user_id,week,delta,balance,reason,actor_id,created) VALUES(?,?,?,?,?,?,?,?)",
                        (r["group_id"], r["user_id"], r["week"], int(r["points"]), int(r["points"]),
                         "Saldo existente antes da auditoria de pontos", None,
                         r["updated"] or datetime.now(timezone.utc).isoformat())
                    )

        # RESET ÚNICO DA TEMPORADA ATUAL — solicitado para corrigir saldos incorretos.
        # Mantém usuários, temporadas anteriores e histórico; zera apenas a temporada ativa
        # uma única vez e registra a compensação no ledger para auditoria.
        reset_flag = c.execute(
            "SELECT value FROM system_flags WHERE key=?",
            ("reset_current_season_points_20260921",),
        ).fetchone()
        if not reset_flag:
            controls = c.execute("SELECT group_id,active_week,status FROM season_control").fetchall()
            for control in controls:
                if control["status"] != "active":
                    continue
                gid = int(control["group_id"])
                week = control["active_week"]
                balances = c.execute(
                    "SELECT user_id,points,updated FROM points WHERE group_id=? AND week=? AND points<>0",
                    (gid, week),
                ).fetchall()
                for row in balances:
                    old_points = int(row["points"])
                    c.execute(
                        "INSERT INTO points_ledger(group_id,user_id,week,delta,balance,reason,actor_id,created) VALUES(?,?,?,?,?,?,?,?)",
                        (gid, int(row["user_id"]), week, -old_points, 0,
                         "Reset único da temporada para correção de pontuação", None,
                         datetime.now(timezone.utc).isoformat()),
                    )
                c.execute("DELETE FROM points WHERE group_id=? AND week=?", (gid, week))
            c.execute(
                "INSERT INTO system_flags(key,value) VALUES(?,?)",
                ("reset_current_season_points_20260921", datetime.now(timezone.utc).isoformat()),
            )

        # Memória visual: migração somente aditiva para permitir expiração
        # automática e evitar que um jogo antigo bloqueie o grupo após restart.
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_games'").fetchone():
            _add_column(c,"memory_games","expires","TEXT")

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,first_seen TEXT,last_seen TEXT,is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY,title TEXT,username TEXT,first_seen TEXT,last_seen TEXT,enabled INTEGER DEFAULT 1,morning INTEGER DEFAULT 1,night INTEGER DEFAULT 1,prize TEXT DEFAULT '',start_time TEXT DEFAULT '10:00',end_time TEXT DEFAULT '00:00',challenge_interval INTEGER DEFAULT 25,challenge_points INTEGER DEFAULT 10,image_chance INTEGER DEFAULT 35,morning_time TEXT DEFAULT '08:00',night_time TEXT DEFAULT '22:00',prize1 TEXT DEFAULT '',prize2 TEXT DEFAULT '',prize3 TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS members(group_id INTEGER,user_id INTEGER,first_seen TEXT,last_seen TEXT,PRIMARY KEY(group_id,user_id));
        CREATE TABLE IF NOT EXISTS points(group_id INTEGER,user_id INTEGER,week TEXT,points INTEGER DEFAULT 0,updated TEXT,PRIMARY KEY(group_id,user_id,week));
        CREATE TABLE IF NOT EXISTS challenges(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,question TEXT,answer TEXT,category TEXT,points INTEGER,status TEXT DEFAULT 'active',winner INTEGER,created TEXT,answered TEXT,media_url TEXT,media_title TEXT,media_revealed INTEGER DEFAULT 0,options_json TEXT,message_id INTEGER,expires TEXT);
        CREATE TABLE IF NOT EXISTS follows(follower INTEGER,followed INTEGER,created TEXT,PRIMARY KEY(follower,followed));
        CREATE TABLE IF NOT EXISTS reactions(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,user_id INTEGER,kind TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,user_id INTEGER,text TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS giveaways(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,prize TEXT,status TEXT DEFAULT 'open',winner INTEGER,created TEXT);
        CREATE TABLE IF NOT EXISTS giveaway_entries(giveaway_id INTEGER,user_id INTEGER,created TEXT,PRIMARY KEY(giveaway_id,user_id));
        CREATE TABLE IF NOT EXISTS weekly_winners(id INTEGER PRIMARY KEY AUTOINCREMENT,group_id INTEGER,week TEXT,user_id INTEGER,points INTEGER,prize TEXT,closed TEXT,UNIQUE(group_id,week));
        CREATE TABLE IF NOT EXISTS group_closing_warnings(group_id INTEGER,day TEXT,created TEXT,PRIMARY KEY(group_id,day));
        CREATE TABLE IF NOT EXISTS season_control(
            group_id INTEGER PRIMARY KEY,
            active_week TEXT NOT NULL,
            opened TEXT NOT NULL,
            closed_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS points_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            week TEXT NOT NULL,
            delta INTEGER NOT NULL,
            balance INTEGER NOT NULL,
            reason TEXT NOT NULL,
            actor_id INTEGER,
            created TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_points_ledger_user ON points_ledger(group_id,user_id,week,created);
        CREATE TABLE IF NOT EXISTS system_flags(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        """)
    migrate_db()
    from database.features import init_features
    init_features()
