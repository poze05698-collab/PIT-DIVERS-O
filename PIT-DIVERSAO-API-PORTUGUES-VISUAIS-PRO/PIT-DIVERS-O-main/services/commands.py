from aiogram import Bot
from aiogram.types import BotCommand,BotCommandScopeAllGroupChats,BotCommandScopeAllPrivateChats
async def setup_commands(bot:Bot):
 group_cs='start pit ajuda desafio adivinha imagem ranking meuspontos perfil quem seguir parar seguidores piada sorte conselho horoscopo quiz dado caraoucoroa parouimpar ppp matematica embaralhada verdadeirooufalso forca feedback giveaway entrargiveaway sortear'.split()
 cs=list(group_cs)
 desc={'start':'Iniciar','pit':'Ligar PIT no grupo','ajuda':'Ajuda','desafio':'Desafio','adivinha':'Adivinha','imagem':'Desafio com imagem','ranking':'Ranking semanal','meuspontos':'Meus pontos','perfil':'Perfil','quem':'Ver perfil','seguir':'Seguir','parar':'Deixar de seguir','seguidores':'Seguidores','piada':'Piada','sorte':'Sorte','conselho':'Conselho','horoscopo':'Horóscopo','quiz':'Quiz','dado':'Dado','caraoucoroa':'Moeda','parouimpar':'Par ou ímpar','ppp':'Pedra papel tesoura','matematica':'Matemática','embaralhada':'Palavra embaralhada','verdadeirooufalso':'Verdadeiro ou falso','forca':'Forca','feedback':'Feedback','giveaway':'Sorteio','entrargiveaway':'Entrar no sorteio','sortear':'Sortear giveaway'}
 group_cmds=[BotCommand(command=x,description=desc.get(x,x)) for x in group_cs]
 private_cmds=group_cmds+[BotCommand(command='admin',description='Painel administrativo')]
 await bot.set_my_commands(group_cmds,scope=BotCommandScopeAllGroupChats())
 await bot.set_my_commands(private_cmds,scope=BotCommandScopeAllPrivateChats())
