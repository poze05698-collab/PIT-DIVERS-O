from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.groups import get, all_groups, toggle, setting, prize
from database.challenges import cancel
from database.points import previous_week, close_week
from services.admin_auth import is_global_admin

router=Router()

class ConfigState(StatesGroup):
    waiting=State()
    kind=State()
    group_id=State()

def home_kb():
    b=InlineKeyboardBuilder()
    b.button(text='👥 Grupos',callback_data='adm:groups')
    b.button(text='⚙️ Configurar grupo',callback_data='adm:choose')
    b.button(text='🎁 Prêmios',callback_data='adm:prizes')
    b.button(text='📊 Status geral',callback_data='adm:status')
    b.adjust(2)
    return b.as_markup()

def group_kb(back='adm:home'):
    b=InlineKeyboardBuilder(); gs=all_groups()
    for g in gs:
        b.button(text=f"🐾 {(g['title'] or 'Grupo')[:30]}",callback_data=f"adm:g:{g['id']}")
    b.button(text='⬅️ Voltar',callback_data=back); b.adjust(1); return b.as_markup()

def settings_kb(gid):
    g=get(gid); b=InlineKeyboardBuilder()
    if not g:return group_kb('adm:choose')
    b.button(text=('🟢 Desligar interação' if g['enabled'] else '🟢 Ligar interação'),callback_data=f'adm:toggle:{gid}')
    b.button(text='⏰ Horário da interação',callback_data=f'adm:hours:{gid}')
    b.button(text='🔁 Intervalo dos desafios',callback_data=f'adm:interval:{gid}')
    b.button(text='⭐ Pontos por desafio',callback_data=f'adm:points:{gid}')
    b.button(text='🖼️ Chance de desafio visual',callback_data=f'adm:image:{gid}')
    b.button(text=('🌅 Desligar bom dia' if g['morning'] else '🌅 Ligar bom dia'),callback_data=f'adm:morning:{gid}')
    b.button(text='🕗 Horário do bom dia',callback_data=f'adm:morningtime:{gid}')
    b.button(text=('🌙 Desligar boa noite' if g['night'] else '🌙 Ligar boa noite'),callback_data=f'adm:night:{gid}')
    b.button(text='🕙 Horário da boa noite',callback_data=f'adm:nighttime:{gid}')
    b.button(text='🎁 Configurar prêmio',callback_data=f'adm:prize:{gid}')
    b.button(text='🧹 Encerrar desafio atual',callback_data=f'adm:cancel:{gid}')
    b.button(text='🏆 Fechar semana',callback_data=f'adm:week:{gid}')
    b.button(text='⬅️ Grupos',callback_data='adm:choose')
    b.adjust(1); return b.as_markup()

def show_group_text(g):
    return (f"⚙️ <b>{g['title'] or 'Grupo'}</b>\n\n"
            f"Interação: {'🟢 ATIVA' if g['enabled'] else '🔴 DESATIVADA'}\n"
            f"🕙 Período: <b>{g['start_time']}</b> até <b>{g['end_time']}</b>\n"
            f"🔁 Intervalo: <b>{g['challenge_interval']} min</b>\n"
            f"⭐ Pontos: <b>{g['challenge_points']}</b>\n"
            f"🖼️ Chance visual: <b>{g['image_chance']}%</b>\n"
            f"🌅 Bom dia: {'🟢' if g['morning'] else '🔴'} às <b>{g['morning_time']}</b>\n"
            f"🌙 Boa noite: {'🟢' if g['night'] else '🔴'} às <b>{g['night_time']}</b>\n"
            f"🎁 Prêmio: <b>{g['prize'] or 'não configurado'}</b>\n\n"
            "Tudo acima pode ser alterado por este painel, sem editar o código.")

async def require_admin(m):
    if not is_global_admin(m.from_user.id):
        await m.answer('⛔ Painel restrito ao administrador principal.')
        return False
    return True

async def require_callback(c):
    if not is_global_admin(c.from_user.id):
        await c.answer('Sem permissão.',show_alert=True); return False
    return True

@router.message(Command('admin'))
async def panel(m:Message):
    if m.chat.type!='private': return await m.answer('🔐 O painel administrativo funciona somente no <b>privado</b> do bot.\n\nAbra o privado e envie <b>/admin</b>.')
    if not await require_admin(m):return
    await m.answer('🛠 <b>PAINEL ADMINISTRATIVO — PIT DIVERSÃO</b>\n\nConfigure grupos, horários, desafios, pontos, prêmio e mensagens pelos botões:',reply_markup=home_kb())

@router.callback_query(F.data=='adm:home')
async def home(c):
    if not await require_callback(c):return
    await c.message.edit_text('🛠 <b>PAINEL ADMINISTRATIVO — PIT DIVERSÃO</b>\n\nEscolha uma opção:',reply_markup=home_kb()); await c.answer()

@router.callback_query(F.data=='adm:groups')
async def groups(c):
    if not await require_callback(c):return
    gs=all_groups(); text='👥 <b>GRUPOS CADASTRADOS</b>\n\n'
    if not gs:text+='Nenhum grupo registrado.'
    for g in gs:text+=f"• {g['title'] or 'Grupo'} — {'🟢 ativo' if g['enabled'] else '🔴 desligado'}\n"
    b=InlineKeyboardBuilder();b.button(text='⚙️ Configurar',callback_data='adm:choose');b.button(text='⬅️ Voltar',callback_data='adm:home');b.adjust(1)
    await c.message.edit_text(text,reply_markup=b.as_markup());await c.answer()

@router.callback_query(F.data=='adm:choose')
async def choose(c):
    if not await require_callback(c):return
    await c.message.edit_text('⚙️ <b>ESCOLHA O GRUPO</b>\n\nTudo será configurado individualmente:',reply_markup=group_kb());await c.answer()

@router.callback_query(F.data.startswith('adm:g:'))
async def group(c):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);g=get(gid)
    if not g:return await c.answer('Grupo não encontrado.',show_alert=True)
    await c.message.edit_text(show_group_text(g),reply_markup=settings_kb(gid));await c.answer()

async def refresh(c,gid,msg=''):
    g=get(gid); await c.message.edit_text(show_group_text(g)+(f'\n\n✅ {msg}' if msg else ''),reply_markup=settings_kb(gid))

@router.callback_query(F.data.startswith('adm:toggle:'))
async def toggle_cb(c):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);g=get(gid);toggle(gid,not bool(g['enabled']));await refresh(c,gid,'Interação atualizada.');await c.answer()

@router.callback_query(F.data.startswith('adm:morning:'))
async def morning(c):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);g=get(gid);setting(gid,'morning',not bool(g['morning']));await refresh(c,gid,'Bom dia atualizado.');await c.answer()

@router.callback_query(F.data.startswith('adm:night:'))
async def night(c):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);g=get(gid);setting(gid,'night',not bool(g['night']));await refresh(c,gid,'Boa noite atualizada.');await c.answer()

async def ask(c,state,gid,kind,title,example):
    await state.set_state(ConfigState.waiting);await state.update_data(group_id=gid,kind=kind)
    await c.message.answer(f'{title}\n\nEnvie o valor.\nExemplo: <b>{example}</b>\n\nEnvie <b>cancelar</b> para desistir.')
    await c.answer()

@router.callback_query(F.data.startswith('adm:hours:'))
async def hours(c,state):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);await ask(c,state,gid,'hours','⏰ <b>HORÁRIO DA INTERAÇÃO</b>','10:00-00:00')

@router.callback_query(F.data.startswith('adm:interval:'))
async def interval(c,state):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);await ask(c,state,gid,'interval','🔁 <b>INTERVALO DOS DESAFIOS</b>','25')

@router.callback_query(F.data.startswith('adm:points:'))
async def points(c,state):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);await ask(c,state,gid,'points','⭐ <b>PONTOS POR DESAFIO</b>','10')

@router.callback_query(F.data.startswith('adm:image:'))
async def image(c,state):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);await ask(c,state,gid,'image','🖼️ <b>CHANCE DE DESAFIO VISUAL</b>','35 (de 0 a 100)')

@router.callback_query(F.data.startswith('adm:morningtime:'))
async def morningtime(c,state):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);await ask(c,state,gid,'morningtime','🕗 <b>HORÁRIO DO BOM DIA</b>','08:00')

@router.callback_query(F.data.startswith('adm:nighttime:'))
async def nighttime(c,state):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);await ask(c,state,gid,'nighttime','🕙 <b>HORÁRIO DA BOA NOITE</b>','22:00')

@router.callback_query(F.data.startswith('adm:prize:'))
async def prize_cb(c,state):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);await ask(c,state,gid,'prize','🎁 <b>PRÊMIO SEMANAL</b>','R$ 50 no Pix')

@router.message(ConfigState.waiting)
async def save_config(m:Message,state:FSMContext):
    if m.chat.type!='private' or not is_global_admin(m.from_user.id):return
    text=(m.text or '').strip()
    if text.lower()=='cancelar':await state.clear();return await m.answer('❌ Alteração cancelada.',reply_markup=home_kb())
    data=await state.get_data();gid=data.get('group_id');kind=data.get('kind');
    try:
        if kind=='hours':
            a,b=[x.strip() for x in text.split('-',1)];
            for x in (a,b):
                h,mi=map(int,x.split(':'))
                if not(0<=h<=23 and 0<=mi<=59):raise ValueError
            setting(gid,'start_time',a);setting(gid,'end_time',b);msg='Horário da interação salvo.'
        elif kind=='interval':
            v=int(text); assert 1<=v<=1440;setting(gid,'challenge_interval',v);msg='Intervalo salvo.'
        elif kind=='points':
            v=int(text);assert 1<=v<=100000;setting(gid,'challenge_points',v);msg='Pontuação salva.'
        elif kind=='image':
            v=int(text);assert 0<=v<=100;setting(gid,'image_chance',v);msg='Chance visual salva.'
        elif kind in ('morningtime','nighttime'):
            h,mi=map(int,text.split(':'));assert 0<=h<=23 and 0<=mi<=59;setting(gid,kind,text);msg='Horário salvo.'
        elif kind=='prize':
            if not text:raise ValueError
            prize(gid,text);msg='Prêmio salvo.'
        else:raise ValueError
    except Exception:
        return await m.answer('❌ Valor inválido. Confira o formato e tente novamente.')
    await state.clear();g=get(gid);await m.answer(show_group_text(g)+f'\n\n✅ {msg}',reply_markup=settings_kb(gid))

@router.callback_query(F.data=='adm:prizes')
async def prizes(c):
    if not await require_callback(c):return
    gs=all_groups();text='🎁 <b>PRÊMIOS DOS GRUPOS</b>\n\n'+''.join(f"• {g['title'] or 'Grupo'}: <b>{g['prize'] or 'não configurado'}</b>\n" for g in gs)
    await c.message.edit_text(text,reply_markup=group_kb());await c.answer()

@router.callback_query(F.data=='adm:status')
async def status(c):
    if not await require_callback(c):return
    gs=all_groups();active=sum(bool(g['enabled']) for g in gs)
    text=f'📊 <b>STATUS GERAL</b>\n\n👥 Grupos: <b>{len(gs)}</b>\n🟢 Interação ativa: <b>{active}</b>\n🤖 Os horários, intervalo, pontos, chance visual, bom dia, boa noite e prêmio são configuráveis pelo painel.'
    b=InlineKeyboardBuilder();b.button(text='⬅️ Voltar',callback_data='adm:home');await c.message.edit_text(text,reply_markup=b.as_markup());await c.answer()

@router.callback_query(F.data.startswith('adm:cancel:'))
async def cancel_cb(c):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);cancel(gid);await refresh(c,gid,'Desafio encerrado.');await c.answer()

@router.callback_query(F.data.startswith('adm:week:'))
async def week_cb(c):
    if not await require_callback(c):return
    gid=int(c.data.split(':')[2]);g=get(gid);result=close_week(gid,previous_week(),g['prize'] or 'Prêmio não configurado')
    await c.answer('Semana fechada.' if result else 'Não há pontuação ou já foi fechada.',show_alert=True);await group(c)

@router.message(Command('interagir','bomdia_on','bomdia_off','boanoite_on','boanoite_off','premio','limpardesafio','fecharsemana','anunciar'))
async def legacy_admin(m:Message):
    if m.chat.type!='private':return await m.answer('🔐 Use <b>/admin</b> no privado do bot.')
    if not await require_admin(m):return
    await m.answer('🛠 Abra <b>/admin</b> para configurar tudo pelos botões.',reply_markup=home_kb())
