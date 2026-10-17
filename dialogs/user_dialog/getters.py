from aiogram import Bot
from aiogram.types import CallbackQuery, User, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.kbd import Button, Select, ManagedMultiselect
from aiogram_dialog.widgets.input import ManagedTextInput

from utils.api import get_account_balance
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG
from constants import SUB_REACTIONS


config: Config = load_config()


async def start_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    try:
        balance = await get_account_balance()
    except Exception:
        balance = 'Ошибка'
    return {
        'balance': balance
    }


async def get_channel(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    channel = text.strip()
    if channel.startswith('@'):
        entered_channel = channel
    elif channel.startswith('https') or channel.startswith('t.me'):
        entered_channel = '@' + channel.split('/')[-1]
    else:
        try:
            entered_channel = int(channel)
        except Exception:
            await msg.answer('❗️Канал не удалось распознать из-за неверного формата ввода, пожалуйста попробуйте снова')
            return

    # блок проверок
    bot_channel = await msg.bot.get_chat(entered_channel)
    if not bot_channel:
        await msg.answer('❗️Бот не нашел канала, проверьте является ли бот участником указанного канала, '
                         'а так же проверьте его админские права в данном канале')
        return

    dialog_manager.dialog_data['channel_id'] = bot_channel.id
    await dialog_manager.switch_to(startSG.select_channel_reaction)


async def channel_reaction_getters(dialog_manager: DialogManager, **kwargs):
    items = [(value.get('reaction'), key) for key, value in SUB_REACTIONS.items()]
    return {
        'items': items
    }


async def select_channel_reaction(clb: CallbackQuery, widget: ManagedMultiselect, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data['reactions'] = widget.get_checked()
    return


async def get_channel_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Кол-во реакций под постом должно быть числом, пожалуйста попробуйте снова')
        return
    if not (10 <= amount <= 1000):
        await msg.answer('❗️Кол-во реакций под постом должно быть не менее 10 и не более 100 (10-1000), '
                         'пожалуйста попробуйте снова')
        return
    dialog_manager.dialog_data['amount'] = amount
    await dialog_manager.switch_to(state=startSG.confirm_save)


async def confirm_save_getter(dialog_manager: DialogManager, **kwargs):
    bot: Bot = dialog_manager.middleware_data.get('bot')

    channel_id = dialog_manager.dialog_data.get('channel_id')
    reactions = dialog_manager.dialog_data.get('reactions')
    amount = dialog_manager.dialog_data.get('amount')

    channel = await bot.get_chat(channel_id)
    reaction_text = ''.join(SUB_REACTIONS[reaction].get('reaction') for reaction in reactions)

    return {
        'name': channel.full_name,
        'reactions': reaction_text,
        'amount': amount
    }


async def save_channels(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    bot: Bot = dialog_manager.middleware_data.get('bot')
    channel_id = dialog_manager.dialog_data.get('channel_id')
    reactions = dialog_manager.dialog_data.get('reactions')
    amount = dialog_manager.dialog_data.get('amount')

    channel = await bot.get_chat(channel_id)

    await session.add_channel(channel_id, channel.full_name, reactions, amount)

    await clb.message.answer('Канал был успешно добавлен')
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(startSG.start)


async def del_channels_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    buttons = dialog_manager.dialog_data.get('del_channel_buttons')
    if not buttons:
        channels = await session.get_channels()
        buttons = [(f'{channel.name}', channel.id) for channel in channels]
        buttons = [buttons[i:i + 10] for i in range(0, len(buttons), 10)]
        dialog_manager.dialog_data['del_channel_buttons'] = buttons
    page = dialog_manager.dialog_data.get('del_page')
    if not page:
        page = 0
        dialog_manager.dialog_data['del_page'] = page
    not_first = False
    not_last = False
    if page != 0:
        not_first = True
    if len(buttons) and page != len(buttons) - 1:
        not_last = True
    return {
        'items': buttons[page] if buttons else [],
        'page': f'{page + 1}/{len(buttons)}',
        'not_first': not_first,
        'not_last': not_last
    }


async def del_channels_pager(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    page = dialog_manager.dialog_data.get('del_page')
    action = clb.data.split('_')[0]
    if action == 'back':
        page -= 1
    else:
        page += 1
    dialog_manager.dialog_data['del_page'] = page
    await dialog_manager.switch_to(startSG.del_channels)


async def del_channel_selector(clb: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data['channel_id'] = int(item_id)
    await dialog_manager.switch_to(startSG.confirm_del_channel)


async def get_del_channel(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    channel = text.strip()
    if channel.startswith('@'):
        entered_channel = channel
    elif channel.startswith('https') or channel.startswith('t.me'):
        entered_channel = '@' + channel.split('/')[-1]
    else:
        try:
            entered_channel = int(channel)
        except Exception:
            await msg.answer('❗️Канал не удалось распознать из-за неверного формата ввода, пожалуйста попробуйте снова')
            return

    session: DataInteraction = dialog_manager.middleware_data.get('session')
    bot: Bot = dialog_manager.middleware_data.get('bot')

    bot_channel = await bot.get_chat(entered_channel)
    if not bot_channel:
        await msg.answer('❗️Данного канала не найдено, пожалуйста попробуйте снова')
        return
    channel = await session.get_channel_by_channel_id(bot_channel.id)
    if not channel:
        await msg.answer('❗️Данного канала не найдено, пожалуйста попробуйте снова')
        return
    dialog_manager.dialog_data['channel_id'] = channel.id
    await dialog_manager.switch_to(startSG.confirm_del_channel)


async def confirm_del_channel_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    channel_id = dialog_manager.dialog_data.get('channel_id')
    channel = await session.get_channel_by_uid(channel_id)
    return {
        'channel': channel.name
    }


async def del_channel(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    channel_id = dialog_manager.dialog_data.get('channel_id')
    await session.del_channel(channel_id)
    await clb.message.answer('Канал был успешно удален')

    dialog_manager.dialog_data.clear()
    channels = await session.get_channels()
    buttons = [(f'{channel.name}', channel.id) for channel in channels]
    buttons = [buttons[i:i + 10] for i in range(0, len(buttons), 10)]
    dialog_manager.dialog_data['del_channel_buttons'] = buttons
    dialog_manager.dialog_data['del_page'] = 0

    await dialog_manager.switch_to(startSG.del_channels)


async def watch_channels_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    channels = await session.get_channels()
    text = ''
    for channel in channels:
        reaction_text = ''.join(SUB_REACTIONS[reaction].get('reaction') for reaction in channel.reactions)
        text = f' - {channel.name}, {channel.amount} - {reaction_text}'
    return {'text': text}


async def choose_channel_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    buttons = dialog_manager.dialog_data.get('change_channel_buttons')
    if not buttons:
        channels = await session.get_channels()
        buttons = [(f'{channel.name}', channel.id) for channel in channels]
        buttons = [buttons[i:i + 10] for i in range(0, len(buttons), 10)]
        dialog_manager.dialog_data['change_channel_buttons'] = buttons
    page = dialog_manager.dialog_data.get('change_page')
    if not page:
        page = 0
        dialog_manager.dialog_data['change_page'] = page
    not_first = False
    not_last = False
    if page != 0:
        not_first = True
    if len(buttons) and page != len(buttons) - 1:
        not_last = True
    return {
        'items': buttons[page] if buttons else [],
        'page': f'{page + 1}/{len(buttons)}',
        'not_first': not_first,
        'not_last': not_last
    }


async def change_channels_pager(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    page = dialog_manager.dialog_data.get('change_page')
    action = clb.data.split('_')[0]
    if action == 'back':
        page -= 1
    else:
        page += 1
    dialog_manager.dialog_data['change_page'] = page
    await dialog_manager.switch_to(startSG.choose_channel)


async def choose_channel_selector(clb: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data['channel_id'] = int(item_id)
    await dialog_manager.switch_to(startSG.change_channel_menu)


async def change_channel_menu_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    channel_id = dialog_manager.dialog_data.get('channel_id')
    channel = await session.get_channel_by_uid(channel_id)
    reaction_text = ''.join(SUB_REACTIONS[reaction].get('reaction') for reaction in channel.reactions)
    text = f' - {channel.name}, {channel.amount} - {reaction_text}'

    return {'text': text}


async def change_channel_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Кол-во реакций под постом должно быть числом, пожалуйста попробуйте снова')
        return
    if not (10 <= amount <= 100):
        await msg.answer('❗️Кол-во реакций под постом должно быть не менее 10 и не более 100 (10-100), '
                         'пожалуйста попробуйте снова')
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    channel_id = dialog_manager.dialog_data.get('channel_id')
    await session.set_channel_value(channel_id, 'amount', amount)

    await msg.answer('Данные для канала были обновлены')

    await dialog_manager.switch_to(state=startSG.change_channel_menu)


async def change_channel_reaction_getter(dialog_manager: DialogManager, **kwargs):
    items = [(value.get('reaction'), key) for key, value in SUB_REACTIONS.items()]
    return {
        'items': items
    }


async def select_changed_channel_reaction(clb: CallbackQuery, widget: ManagedMultiselect, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data['reactions'] = widget.get_checked()
    return


async def change_channel_reactions(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    channel_id = dialog_manager.dialog_data.get('channel_id')
    reactions = dialog_manager.dialog_data.get('reactions')

    await session.set_channel_value(channel_id, 'reactions', reactions)

    await clb.message.answer('Данные для канала были обновлены')

    await dialog_manager.switch_to(state=startSG.change_channel_menu)




