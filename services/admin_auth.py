import os
from config import ADMIN_IDS


def get_admin_ids():
    ids = set(ADMIN_IDS or set())
    for key in ('ADMIN_IDS', 'ADMIN_ID'):
        raw = os.getenv(key, '')
        for value in raw.replace(';', ',').split(','):
            value = value.strip()
            if value.lstrip('-').isdigit():
                ids.add(int(value))
    return ids


def is_global_admin(user_id: int) -> bool:
    try:
        return int(user_id) in get_admin_ids()
    except (TypeError, ValueError):
        return False
