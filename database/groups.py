from database.connection import get_connection


def upsert_group(chat):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO groups (id, title, username)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                username = excluded.username
        """, (chat.id, chat.title or "Grupo", getattr(chat, "username", None)))
        conn.commit()
    finally:
        conn.close()


def is_enabled(group_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT entertainment_enabled FROM groups WHERE id = ?", (group_id,)
        ).fetchone()
        return bool(row["entertainment_enabled"]) if row else True
    finally:
        conn.close()


def set_enabled(group_id, enabled):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE groups SET entertainment_enabled = ? WHERE id = ?",
            (1 if enabled else 0, group_id),
        )
        conn.commit()
    finally:
        conn.close()
