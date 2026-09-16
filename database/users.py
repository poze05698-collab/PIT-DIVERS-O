from database.connection import get_connection


def upsert_user(user):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO users (id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                is_active = 1
        """, (user.id, user.username, user.first_name or "Usuário"))
        conn.commit()
    finally:
        conn.close()


def register_group_member(group_id, user_id):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO group_members (group_id, user_id)
            VALUES (?, ?)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                last_seen_at = CURRENT_TIMESTAMP
        """, (group_id, user_id))
        conn.commit()
    finally:
        conn.close()
