from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from config import TIMEZONE
from database.connection import db


def now():
    """Timestamp absoluto em UTC, usado para auditoria/ordenação."""
    return datetime.now(timezone.utc).isoformat()


def _local_now():
    return datetime.now(ZoneInfo(TIMEZONE))


def wk(dt=None):
    """Semana ISO do calendário local. Usada como referência inicial/legado."""
    if dt is None:
        d = _local_now().date()
    elif getattr(dt, "tzinfo", None) is not None:
        d = dt.astimezone(ZoneInfo(TIMEZONE)).date()
    else:
        d = dt.date()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def ensure_season(gid):
    """Garante uma temporada ativa sem trocar automaticamente por mudança de data."""
    with db() as c:
        r = c.execute(
            "SELECT active_week FROM season_control WHERE group_id=?",
            (gid,),
        ).fetchone()
        if r:
            return r["active_week"]
        latest = c.execute(
            "SELECT week FROM points WHERE group_id=? ORDER BY updated DESC LIMIT 1",
            (gid,),
        ).fetchone()
        active_week = latest["week"] if latest else wk()
        c.execute(
            "INSERT INTO season_control(group_id,active_week,opened,closed_count) VALUES(?,?,?,0)",
            (gid, active_week, now()),
        )
        return active_week


def active_week(gid):
    return ensure_season(gid)


def season_status(gid):
    ensure_season(gid)
    with db() as c:
        r = c.execute("SELECT active_week,status,closed_count,opened FROM season_control WHERE group_id=?", (gid,)).fetchone()
        return dict(r) if r else {"active_week": ensure_season(gid), "status": "active", "closed_count": 0, "opened": now()}


def season_is_active(gid):
    return season_status(gid)["status"] == "active"


def _next_week_key(gid, old_week):
    """Cria uma chave única para a nova temporada manual."""
    base = wk()
    with db() as c:
        # Mantém a identificação legível e permite várias temporadas abertas
        # manualmente dentro da mesma semana do calendário.
        n = c.execute(
            "SELECT COUNT(*) n FROM weekly_seasons WHERE group_id=?",
            (gid,),
        ).fetchone()["n"]
        candidate = f"{base}-S{int(n) + 1}"
        while c.execute(
            "SELECT 1 FROM points WHERE group_id=? AND week=? LIMIT 1",
            (gid, candidate),
        ).fetchone():
            n += 1
            candidate = f"{base}-S{int(n) + 1}"
        return candidate


def add(g, u, n, reason="Pontos", actor_id=None):
    """Adiciona pontos de forma atômica e registra cada alteração no ledger."""
    n = int(n)
    if n == 0:
        return mine(g, u)
    with db() as c:
        r = c.execute(
            "SELECT active_week,status FROM season_control WHERE group_id=?",
            (g,),
        ).fetchone()
        if r:
            if r["status"] != "active":
                raise RuntimeError("A temporada está encerrada. O administrador precisa iniciar uma nova temporada.")
            week = r["active_week"]
        else:
            latest = c.execute(
                "SELECT week FROM points WHERE group_id=? ORDER BY updated DESC LIMIT 1",
                (g,),
            ).fetchone()
            week = latest["week"] if latest else wk()
            c.execute(
                "INSERT OR IGNORE INTO season_control(group_id,active_week,opened,closed_count) VALUES(?,?,?,0)",
                (g, week, now()),
            )
        current = c.execute(
            "SELECT points FROM points WHERE group_id=? AND user_id=? AND week=?",
            (g, u, week),
        ).fetchone()
        old_balance = int(current["points"]) if current else 0
        new_balance = old_balance + n
        if new_balance < 0:
            raise ValueError("Saldo de pontos não pode ficar negativo.")
        c.execute(
            "INSERT INTO points(group_id,user_id,week,points,updated) VALUES(?,?,?,?,?) "
            "ON CONFLICT(group_id,user_id,week) DO UPDATE SET "
            "points=excluded.points,updated=excluded.updated",
            (g, u, week, new_balance, now()),
        )
        c.execute(
            "INSERT INTO points_ledger(group_id,user_id,week,delta,balance,reason,actor_id,created) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (g, u, week, n, new_balance, str(reason)[:200], actor_id, now()),
        )
        return new_balance


def set_points(g, u, value, reason="Ajuste administrativo", actor_id=None):
    """Define um saldo exato na temporada ativa e registra a diferença.

    O ajuste administrativo também respeita o estado da temporada. Isso evita
    que uma chamada antiga/concorrente consiga recriar pontos depois que o
    administrador encerrou a temporada.
    """
    value = int(value)
    if value < 0:
        raise ValueError("Saldo não pode ser negativo.")
    with db() as c:
        r = c.execute(
            "SELECT active_week,status FROM season_control WHERE group_id=?",
            (g,),
        ).fetchone()
        if r and r["status"] != "active":
            raise RuntimeError("A temporada está encerrada. O administrador precisa iniciar uma nova temporada.")
        week = r["active_week"] if r else wk()
        current = c.execute(
            "SELECT points FROM points WHERE group_id=? AND user_id=? AND week=?",
            (g, u, week),
        ).fetchone()
        old = int(current["points"]) if current else 0
        delta = value - old
        if delta == 0:
            return old
        c.execute(
            "INSERT INTO points(group_id,user_id,week,points,updated) VALUES(?,?,?,?,?) "
            "ON CONFLICT(group_id,user_id,week) DO UPDATE SET points=excluded.points,updated=excluded.updated",
            (g, u, week, value, now()),
        )
        c.execute(
            "INSERT INTO points_ledger(group_id,user_id,week,delta,balance,reason,actor_id,created) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (g, u, week, delta, value, str(reason)[:200], actor_id, now()),
        )
        return value


def mine(g, u):
    if not season_is_active(g):
        return 0
    with db() as c:
        r = c.execute(
            "SELECT points FROM points WHERE group_id=? AND user_id=? AND week=?",
            (g, u, active_week(g)),
        ).fetchone()
        return int(r["points"]) if r else 0


def rank(g, limit=10, week=None):
    if week is None and not season_is_active(g):
        return []
    week = week or active_week(g)
    with db() as c:
        return c.execute(
            "SELECT p.user_id,p.points,u.first_name,u.username "
            "FROM points p JOIN users u ON u.id=p.user_id "
            "WHERE p.group_id=? AND p.week=? "
            "ORDER BY p.points DESC,p.updated ASC LIMIT ?",
            (g, week, limit),
        ).fetchall()


def users_with_points(g, limit=10, offset=0):
    """Membros do grupo com saldo da temporada ativa; durante o intervalo fechado, saldo exibido é zero."""
    week = active_week(g)
    if not season_is_active(g):
        with db() as c:
            return c.execute(
                "SELECT m.user_id,u.first_name,u.username,0 points FROM members m JOIN users u ON u.id=m.user_id WHERE m.group_id=? ORDER BY u.first_name COLLATE NOCASE ASC LIMIT ? OFFSET ?",
                (g, limit, offset),
            ).fetchall()
    with db() as c:
        return c.execute(
            "SELECT m.user_id, u.first_name,u.username, "
            "COALESCE(p.points,0) points "
            "FROM members m JOIN users u ON u.id=m.user_id "
            "LEFT JOIN points p ON p.group_id=m.group_id AND p.user_id=m.user_id AND p.week=? "
            "WHERE m.group_id=? "
            "ORDER BY points DESC, u.first_name COLLATE NOCASE ASC "
            "LIMIT ? OFFSET ?",
            (week, g, limit, offset),
        ).fetchall()


def user_points_summary(g, u):
    with db() as c:
        current = active_week(g)
        current_value = 0 if not season_is_active(g) else None
        row = c.execute(
            "SELECT COALESCE(SUM(points),0) total, "
            "COALESCE(MAX(CASE WHEN week=? THEN points END),0) current "
            "FROM points WHERE group_id=? AND user_id=?",
            (current,g,u),
        ).fetchone()
        seasons = c.execute(
            "SELECT week,points,updated FROM points WHERE group_id=? AND user_id=? ORDER BY updated DESC",
            (g,u),
        ).fetchall()
        return {
            "current": int(current_value if current_value is not None else (row["current"] or 0)),
            "total": int(row["total"] or 0),
            "week": current,
            "seasons": seasons,
        }


def find_group_user(g, query):
    q = str(query).strip()
    if not q:
        return []
    week = active_week(g)
    if not season_is_active(g):
        with db() as c:
            if q.lstrip("-").isdigit():
                return c.execute(
                    "SELECT m.user_id,u.first_name,u.username,0 points FROM members m JOIN users u ON u.id=m.user_id "
                    "WHERE m.group_id=? AND m.user_id=? LIMIT 10",
                    (g,int(q)),
                ).fetchall()
            return c.execute(
                "SELECT m.user_id,u.first_name,u.username,0 points FROM members m JOIN users u ON u.id=m.user_id "
                "WHERE m.group_id=? AND (LOWER(COALESCE(u.first_name,'')) LIKE LOWER(?) OR LOWER(COALESCE(u.username,'')) LIKE LOWER(?)) "
                "ORDER BY u.first_name COLLATE NOCASE LIMIT 10",
                (g,f"%{q.lstrip('@')}%",f"%{q.lstrip('@')}%"),
            ).fetchall()
    with db() as c:
        if q.lstrip("-").isdigit():
            return c.execute(
                "SELECT m.user_id,u.first_name,u.username,COALESCE(p.points,0) points "
                "FROM members m JOIN users u ON u.id=m.user_id "
                "LEFT JOIN points p ON p.group_id=m.group_id AND p.user_id=m.user_id AND p.week=? "
                "WHERE m.group_id=? AND m.user_id=? LIMIT 10",
                (week,g,int(q)),
            ).fetchall()
        return c.execute(
            "SELECT m.user_id,u.first_name,u.username,COALESCE(p.points,0) points "
            "FROM members m JOIN users u ON u.id=m.user_id "
            "LEFT JOIN points p ON p.group_id=m.group_id AND p.user_id=m.user_id AND p.week=? "
            "WHERE m.group_id=? AND (LOWER(COALESCE(u.first_name,'')) LIKE LOWER(?) "
            "OR LOWER(COALESCE(u.username,'')) LIKE LOWER(?)) "
            "ORDER BY points DESC LIMIT 10",
            (week,g,f"%{q.lstrip('@')}%",f"%{q.lstrip('@')}%"),
        ).fetchall()

def close_season(gid, week=None, prizes=None):
    """Encerra apenas a temporada atual. A nova temporada NÃO é criada aqui.
    O início e o zeramento do saldo da nova temporada acontecem em start_new_season().
    """
    prizes = prizes or ["Prêmio não configurado"] * 3
    with db() as c:
        control = c.execute(
            "SELECT active_week,status,closed_count FROM season_control WHERE group_id=?",
            (gid,),
        ).fetchone()
        if not control:
            old_week = week or wk()
            c.execute(
                "INSERT INTO season_control(group_id,active_week,opened,closed_count,status) VALUES(?,?,?,0,'active')",
                (gid, old_week, now()),
            )
            status = "active"
            closed_count = 0
        else:
            old_week = control["active_week"]
            status = control["status"]
            closed_count = int(control["closed_count"] or 0)
        if status != "active":
            return None

        rows = c.execute(
            "SELECT p.user_id,p.points,u.first_name,u.username "
            "FROM points p JOIN users u ON u.id=p.user_id "
            "WHERE p.group_id=? AND p.week=? "
            "ORDER BY p.points DESC,p.updated ASC LIMIT 3",
            (gid, old_week),
        ).fetchall()
        vals=[]
        for i in range(3):
            r=rows[i] if i < len(rows) else None
            vals.extend([
                r["user_id"] if r else None,
                int(r["points"]) if r else 0,
                prizes[i] if i < len(prizes) else "Prêmio não configurado",
            ])
        c.execute(
            "INSERT INTO weekly_seasons(group_id,week,closed,winner1,points1,prize1,winner2,points2,prize2,winner3,points3,prize3) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (gid,old_week,now(),*vals),
        )
        # Bloqueia imediatamente qualquer recompensa da temporada encerrada.
        c.execute("UPDATE challenges SET status='expired' WHERE group_id=? AND status='active'", (gid,))
        c.execute("UPDATE memory_games SET status='expired' WHERE group_id=? AND status='active'", (gid,))
        c.execute("UPDATE chest_releases SET active=0,active_until=? WHERE group_id=? AND active=1", (now(),gid))
        c.execute("UPDATE season_control SET status='closed' WHERE group_id=?", (gid,))
        return {"rows": rows, "old_week": old_week, "new_week": None, "closed_count": closed_count}


def start_new_season(gid):
    """Abre uma nova temporada e garante saldo inicial zero. Só funciona após o fechamento."""
    with db() as c:
        control = c.execute(
            "SELECT active_week,status,closed_count FROM season_control WHERE group_id=?",
            (gid,),
        ).fetchone()
        if not control or control["status"] != "closed":
            return None
        old_week = control["active_week"]
        count = int(control["closed_count"] or 0) + 1
        base = wk()
        new_week = f"{base}-S{count}"
        while c.execute("SELECT 1 FROM points WHERE group_id=? AND week=? LIMIT 1", (gid,new_week)).fetchone():
            count += 1
            new_week = f"{base}-S{count}"
        # A nova chave começa sem nenhum saldo. Não apagamos o histórico antigo.
        c.execute("DELETE FROM points WHERE group_id=? AND week=?", (gid,new_week))
        c.execute(
            "UPDATE season_control SET active_week=?,opened=?,closed_count=?,status='active' WHERE group_id=?",
            (new_week,now(),count,gid),
        )
        return {"old_week": old_week, "new_week": new_week}

def season_history(gid,limit=10):
    with db() as c:
        return c.execute(
            "SELECT * FROM weekly_seasons WHERE group_id=? ORDER BY id DESC LIMIT ?",
            (gid,limit),
        ).fetchall()


def points_ledger(gid, uid=None, limit=30):
    with db() as c:
        if uid is None:
            return c.execute(
                "SELECT * FROM points_ledger WHERE group_id=? ORDER BY id DESC LIMIT ?",
                (gid,limit),
            ).fetchall()
        return c.execute(
            "SELECT * FROM points_ledger WHERE group_id=? AND user_id=? ORDER BY id DESC LIMIT ?",
            (gid,uid,limit),
        ).fetchall()


def close_week(g, week, prize):
    # Compatibilidade com versões antigas; o fechamento oficial usa close_season().
    with db() as c:
        r=c.execute(
            "SELECT p.user_id,p.points,u.first_name,u.username FROM points p JOIN users u ON u.id=p.user_id "
            "WHERE p.group_id=? AND p.week=? ORDER BY p.points DESC,p.updated ASC LIMIT 1",
            (g,week),
        ).fetchone()
        return r


def previous_week():
    return wk(_local_now() - timedelta(days=1))
