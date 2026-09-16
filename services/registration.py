from database.groups import upsert_group
from database.users import upsert_user, register_group_member


def register_message_context(message):
    if message.from_user:
        upsert_user(message.from_user)

    if message.chat.type in {"group", "supergroup"}:
        upsert_group(message.chat)
        if message.from_user:
            register_group_member(message.chat.id, message.from_user.id)
