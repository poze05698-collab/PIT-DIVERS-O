from aiogram import Bot
from aiogram.enums import ChatMemberStatus
async def admin(bot:Bot,chat:int,user:int):
 try:return (await bot.get_chat_member(chat,user)).status in {ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.CREATOR}
 except:return False
