from config import ADMIN_IDS

def is_global_admin(user_id: int) -> bool:
    return int(user_id) in ADMIN_IDS
