from datetime import datetime, timezone

from database.connection import db


def now():
    return datetime.now(timezone.utc).isoformat()


def upsert(u):
    """Create/update a user without relying on the physical column order.

    This is important for upgrades: older PIT DIVERSÃO databases may have
    only the original 5 user columns and therefore cannot accept a 6-value
    INSERT INTO users VALUES(...).
    """
    timestamp = now()
    with db() as c:
        c.execute(
            """
            INSERT INTO users (id, username, first_name, first_seen, last_seen, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_seen=excluded.last_seen,
                is_active=1
            """,
            (
                u.id,
                u.username,
                u.first_name or "Usuário",
                timestamp,
                timestamp,
            ),
        )


def get(uid):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
