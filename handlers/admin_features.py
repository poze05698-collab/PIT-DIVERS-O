from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.admin_auth import is_global_admin
from database.groups import all_groups, get, setting
from database.features import settings, toggle, set_value, activate_chest

router=Router(name='admin_features')

class FS(StatesGroup):
    value=State()

def groups_kb():
    b=InlineKeyboardBuilder()
    for g in all_groups(): b.button(text=f'🐾 {(g["title"] or "Grupo")[:30]}',callback_data=f'afs:g:{g["id"]}')
    b.button(text='⬅️ Voltar',callback_data='afs:back')
    b.adjust(1); return b.as_markup()

def sys_kb(gid):
    s=settings(gid); b=InlineKeyboardBuilder()
    labels=[('xp_enabled','⭐ XP / níveis'),('combo_enabled','🔥 Combos'),('achievements_enabled','🏅 Conquistas'),('missions_enabled','🎯 Missões'),('chest_enabled','🎁 Baú diário'),('battles_enabled','⚔️ Batalha 1x1'),('memory_enabled','🧠 Memória visual'),('events_enabled','🎉 Eventos'),('category_rank_enabled','📊 Ranking por categoria'),('victory_messages_enabled','💬 Mensagens variadas'),('howto_enabled','📖 Como funciona')]
    for field,label in labels: b.button(text=('🟢 ' if s[field] else '🔴 ')+label,callback_data=f'afs:t:{gid}:{field}')
    b.button(text='⚔️ Configurar Batalha 1x1',callback_data=f'afs:battlecfg:{gid}')
    b.button(text='🎯 Configurar Missões Diárias',callback_data=f'afs:missioncfg:{gid}')
    b.button(text='🎁 Liberar baú agora',callback_data=f'afs:chest:{gid}')
    b.button(text='⏱️ Tempo do baú',callback_data=f'afs:chesttime:{gid}')
    b.button(text='🎁 Prêmios TOP 3',callback_data=f'afs:p:{gid}')
    b.button(text='⚙️ Valores',callback_data=f'afs:v:{gid}')
    b.button(text='⬅️ Grupos',callback_data='afs:groups'); b.adjust(1); return b.as_markup()

def sys_text(gid):
    g=get(gid); s=settings(gid)
    return f'⚙️ <b>SISTEMAS — {g["title"] if g else "Grupo"}</b>\n\n🟢 = ligado | 🔴 = desligado\n\n⭐ XP: {"🟢" if s["xp_enabled"] else "🔴"}\n🔥 Combos: {"🟢" if s["combo_enabled"] else "🔴"}\n🏅 Conquistas: {"🟢" if s["achievements_enabled"] else "🔴"}\n🎯 Missões: {"🟢" if s["missions_enabled"] else "🔴"}\n🎁 Baú: {"🟢" if s["chest_enabled"] else "🔴"}\n⚔️ Batalha: {"🟢" if s["battles_enabled"] else "🔴"}\n🧠 Memória: {"🟢" if s["memory_enabled"] else "🔴"}\n🎉 Eventos: {"🟢" if s["events_enabled"] else "🔴"}\n📊 Ranking categoria: {"🟢" if s["category_rank_enabled"] else "🔴"}\n💬 Mensagens: {"🟢" if s["victory_messages_enabled"] else "🔴"}\n📖 Como funciona: {"🟢" if s["howto_enabled"] else "🔴"}'

async def guard(m):
    return m.chat.type=='private' and is_global_admin(m.from_user.id)
async def cguard(c):
    return is_global_admin(c.from_user.id)

@router.message(Command('sistemas'))
async def systems_cmd(m):
    if not await guard(m): return
    await m.answer('⚙️ <b>SISTEMAS</b>\nEscolha o grupo:',reply_markup=groups_kb())

@router.callback_query(F.data=='adm:systems')
async def systems(c):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    await c.message.edit_text('⚙️ <b>SISTEMAS</b>\nEscolha o grupo:',reply_markup=groups_kb()); await c.answer()

@router.callback_query(F.data=='afs:groups')
async def groups(c):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    await c.message.edit_text('⚙️ <b>SISTEMAS</b>\nEscolha o grupo:',reply_markup=groups_kb()); await c.answer()

@router.callback_query(F.data.startswith('afs:g:'))
async def group(c):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    gid=int(c.data.split(':')[2]); await c.message.edit_text(sys_text(gid),reply_markup=sys_kb(gid)); await c.answer()

@router.callback_query(F.data.startswith('afs:t:'))
async def toggle_cb(c):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    _,_,gid,field=c.data.split(':'); gid=int(gid)
    enabled=toggle(gid,field)
    # Ao ligar missões/batalhas, avisa o grupo imediatamente. Desligar apenas
    # impede novas utilizações; dados e histórico existentes são preservados.
    if enabled and field in {'missions_enabled','battles_enabled'}:
        messages={
            'missions_enabled':'🎯 <b>MISSÕES DIÁRIAS ATIVADAS!</b>\n\nConfira sua missão com /missao e participe dos desafios para completar sua meta. 🔥',
            'battles_enabled':'⚔️ <b>BATALHA 1x1 LIBERADA!</b>\n\nEntre na batalha 1x1 e convide seu amigo para uma disputa! 🔥\nUse /batalha respondendo à mensagem do adversário.'
        }
        try: await c.bot.send_message(gid,messages[field])
        except Exception: pass
    await c.message.edit_text(sys_text(gid),reply_markup=sys_kb(gid)); await c.answer('Configuração salva.')

@router.callback_query(F.data.startswith('afs:battlecfg:'))
async def battle_cfg(c):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    gid=int(c.data.split(':')[2]); s=settings(gid)
    b=InlineKeyboardBuilder(); b.button(text=('🟢 Desativar' if s['battles_enabled'] else '🔴 Ativar'),callback_data=f'afs:t:{gid}:battles_enabled'); b.button(text='⚔️ Alterar recompensa',callback_data=f'afs:vv:{gid}:battle_points'); b.button(text='⬅️ Sistemas',callback_data=f'afs:g:{gid}'); b.adjust(1)
    await c.message.edit_text(f'⚔️ <b>BATALHA 1x1</b>\n\nStatus: {"🟢 ATIVA" if s["battles_enabled"] else "🔴 DESATIVADA"}\nRecompensa: <b>{s["battle_points"]} pontos</b>\n\nA batalha será disputada por botões e o primeiro a acertar vence.',reply_markup=b.as_markup()); await c.answer()

@router.callback_query(F.data.startswith('afs:missioncfg:'))
async def mission_cfg(c):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    gid=int(c.data.split(':')[2]); s=settings(gid)
    b=InlineKeyboardBuilder(); b.button(text=('🟢 Desativar' if s['missions_enabled'] else '🔴 Ativar'),callback_data=f'afs:t:{gid}:missions_enabled'); b.button(text='🎯 Alterar meta',callback_data=f'afs:vv:{gid}:mission_target'); b.button(text='🎁 Alterar recompensa',callback_data=f'afs:vv:{gid}:mission_reward'); b.button(text='⬅️ Sistemas',callback_data=f'afs:g:{gid}'); b.adjust(1)
    await c.message.edit_text(f'🎯 <b>MISSÕES DIÁRIAS</b>\n\nStatus: {"🟢 ATIVAS" if s["missions_enabled"] else "🔴 DESATIVADAS"}\nMeta: <b>{s["mission_target"]}</b>\nRecompensa: <b>{s["mission_reward"]} pontos</b>\n\nO progresso é salvo por usuário e por dia.',reply_markup=b.as_markup()); await c.answer()

@router.callback_query(F.data.startswith('afs:chest:'))
async def release_chest(c, state: FSMContext):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    gid=int(c.data.split(':')[2]); s=settings(gid)
    if not s['chest_enabled']:
        return await c.answer('Ative o Baú Diário primeiro.',show_alert=True)
    minutes=max(1,int(s['chest_duration_minutes'] or 10))
    activate_chest(gid,minutes)
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🎁 ABRIR MEU BAÚ',callback_data=f'feature:chest:{gid}')]])
        await c.bot.send_message(gid,f'🎁 <b>BAÚ DIÁRIO LIBERADO!</b>\n\nO baú está disponível por <b>{minutes} minutos</b>!\n\n👇 Clique abaixo para abrir seu baú.',reply_markup=kb)
    except Exception:
        return await c.answer('Não consegui anunciar no grupo. Verifique as permissões do bot.',show_alert=True)
    await c.answer(f'Baú liberado por {minutes} minutos.')

@router.callback_query(F.data.startswith('afs:chesttime:'))
async def chest_time(c,state: FSMContext):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    gid=int(c.data.split(':')[2]); await state.set_state(FS.value); await state.update_data(kind='chest_duration_minutes',gid=gid)
    await c.message.answer('⏱️ <b>TEMPO DO BAÚ</b>\n\nEnvie quantos minutos o baú ficará aberto.\nEx.: <b>10</b>\n\nDigite <b>cancelar</b> para sair.')
    await c.answer()

@router.callback_query(F.data.startswith('afs:p:'))
async def prizes(c):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    gid=int(c.data.split(':')[2]); g=get(gid); b=InlineKeyboardBuilder()
    for i in range(1,4): b.button(text=f'{["🥇","🥈","🥉"][i-1]} Prêmio {i}',callback_data=f'afs:pp:{gid}:{i}')
    b.button(text='⬅️ Sistemas',callback_data=f'afs:g:{gid}'); b.adjust(1)
    await c.message.edit_text(f'🎁 <b>PRÊMIOS TOP 3</b>\n\n🥇 {g["prize1"] or "não configurado"}\n🥈 {g["prize2"] or "não configurado"}\n🥉 {g["prize3"] or "não configurado"}',reply_markup=b.as_markup()); await c.answer()

@router.callback_query(F.data.startswith('afs:pp:'))
async def prize_prompt(c,state: FSMContext):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    _,_,gid,pos=c.data.split(':'); await state.set_state(FS.value); await state.update_data(kind='prize'+pos,gid=int(gid)); await c.message.answer(f'🎁 Envie o prêmio do <b>{pos}º lugar</b>.\nEx.: R$ 100 ou Banca 100\n\nDigite <b>cancelar</b> para sair.'); await c.answer()

@router.callback_query(F.data.startswith('afs:v:'))
async def values(c):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    gid=int(c.data.split(':')[2]); s=settings(gid); b=InlineKeyboardBuilder()
    for field,label in [('xp_per_answer','XP por acerto'),('combo_bonus','Bônus do combo'),('chest_points','Pontos do baú'),('mission_target','Meta da missão'),('mission_reward','🎯 Recompensa da missão'),('battle_points','⚔️ Pontos da batalha')]: b.button(text=label,callback_data=f'afs:vv:{gid}:{field}')
    b.button(text='📖 Texto como funciona',callback_data=f'afs:how:{gid}'); b.button(text='⬅️ Sistemas',callback_data=f'afs:g:{gid}'); b.adjust(1)
    await c.message.edit_text(f'⚙️ <b>VALORES</b>\n\nXP/acerto: {s["xp_per_answer"]}\nCombo: {s["combo_bonus"]}\nBaú: {s["chest_points"]}\nMeta missão: {s["mission_target"]}\nBatalha: {s["battle_points"]}\nEvento: x{s["event_multiplier"]}',reply_markup=b.as_markup()); await c.answer()

@router.callback_query(F.data.startswith('afs:vv:'))
async def value_prompt(c,state: FSMContext):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    _,_,gid,field=c.data.split(':'); await state.set_state(FS.value); await state.update_data(kind=field,gid=int(gid)); await c.message.answer('✏️ Envie o novo valor:'); await c.answer()

@router.callback_query(F.data.startswith('afs:how:'))
async def how_prompt(c,state: FSMContext):
    if not await cguard(c): return await c.answer('Sem permissão.',show_alert=True)
    gid=int(c.data.split(':')[2]); await state.set_state(FS.value); await state.update_data(kind='howto_text',gid=gid); await c.message.answer('📖 Envie o texto. Use <code>{member}</code> para marcar o membro.'); await c.answer()

@router.message(FS.value)
async def save_value(m,state: FSMContext):
    if not await guard(m): return
    data=await state.get_data(); gid=int(data['gid']); kind=data['kind']; text=(m.text or '').strip()
    if text.lower() == 'cancelar':
        await state.clear(); return await m.answer('❌ Alteração cancelada.')
    if kind.startswith('prize'):
        if not text: return await m.answer('❌ Informe o prêmio ou digite cancelar.')
        pos=kind[-1]; setting(gid,'prize'+pos,text)
    elif kind=='howto_text': set_value(gid,kind,text)
    elif kind=='chest_duration_minutes':
        v=int(text)
        if not 1<=v<=1440: raise ValueError
        set_value(gid,kind,v)
    else:
        try: v=int(text); 
        except: return await m.answer('❌ Envie apenas um número.')
        if v<1 or v>100000: return await m.answer('❌ Valor fora do limite.')
        set_value(gid,kind,v)
    await state.clear(); await m.answer('✅ Configuração salva.')
