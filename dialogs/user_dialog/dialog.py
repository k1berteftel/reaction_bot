from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Group, Select, Start, Url, Multiselect
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

from dialogs.user_dialog import getters

from states.state_groups import startSG, adminSG

user_dialog = Dialog(
    Window(
        Const('Главное меню'),
        Format('Баланс аккаунта: {balance}₽'),
        Column(
            SwitchTo(Const('Добавить канал'), id='get_channel_switcher', state=startSG.get_channel),
            SwitchTo(Const('Удалить канал'), id='del_parse_channels_switcher', state=startSG.del_channels),
            SwitchTo(Const('Просмотреть каналы'), id='show_channels_switcher', state=startSG.watch_channels),
        ),
        getter=getters.start_getter,
        state=startSG.start
    ),
    Window(
        Const('Введите ссылку/юзер/id канала\n\nДопустимый '
              'формат ввода:\n'
              'https://t.me/room_RO (ссылка)\n@room_RO (юзернейм)\n-1001053645184 (ID)'),
        TextInput(
            id='get_channel',
            on_success=getters.get_channel
        ),
        SwitchTo(Const('◀️Назад'), id='back', state=startSG.start),
        state=startSG.get_channel
    ),
    Window(
        Const('Выберите доп. реакции для накрутки:'),
        Group(
            Multiselect(
                Format('✔️ {item[0]}'),
                Format('{item[0]}'),
                id='reactions_builder',
                item_id_getter=lambda x: x[1],
                items='items',
                on_click=getters.select_channel_reaction,
                min_selected=1
            ),
            width=2
        ),
        SwitchTo(Const('Сохранить выбор'), id='get_channel_amount_switcher', state=startSG.get_channel_amount),
        SwitchTo(Const('◀️Назад'), id='back_get_channel', state=startSG.get_channel),
        getter=getters.channel_reaction_getters,
        state=startSG.select_channel_reaction
    ),
    Window(
        Const('Введите количество реакций на посту (10-1000)'),
        TextInput(
            id='get_channel_amount',
            on_success=getters.get_channel_amount
        ),
        SwitchTo(Const('◀️Назад'), id='back_select_channel_reaction', state=startSG.select_channel_reaction),
        state=startSG.get_channel_amount
    ),
    Window(
        Format('Сохраняем выбранный канал:\n - Канал: {name}\n - Выбранные реакции: {reactions}\n - Кол-во реакций: {amount}'),
        Row(
            Button(Const('Подтвердить'), id='save_channels', on_click=getters.save_channels),
            SwitchTo(Const('Отмена'), id='save_cancel', state=startSG.start),
        ),
        SwitchTo(Const('◀️Назад'), id='back_warning_count', state=startSG.get_channel_amount),
        getter=getters.confirm_save_getter,
        state=startSG.confirm_save
    ),
    Window(
        Const('Введите ссылку/юзер/id канала, который вы хотели бы удалить или же выберите канал ниже:'),
        TextInput(
            id='get_del_channel',
            on_success=getters.get_del_channel
        ),
        Group(
            Select(
                Format('{item[0]}'),
                id='del_channels_builder',
                item_id_getter=lambda x: x[1],
                items='items',
                on_click=getters.del_channel_selector
            ),
            width=1
        ),
        Row(
            Button(Const('◀️'), id='back_del_channel_pager', on_click=getters.del_channels_pager, when='not_first'),
            Button(Format('{page}'), id='del_channel_pager', when='items'),
            Button(Const('▶️'), id='next_del_channel_pager', on_click=getters.del_channels_pager, when='not_last')
        ),
        SwitchTo(Const('Назад'), id='back', state=startSG.start),
        getter=getters.del_channels_getter,
        state=startSG.del_channels
    ),
    Window(
        Format('Вы действительно хотите удалить данный канал "{channel}"'),
        Row(
            Button(Const('Да'), id='del_channel', on_click=getters.del_channel),
            SwitchTo(Const('Отмена'), id='back_del_channels', state=startSG.del_channels),
        ),
        getter=getters.confirm_del_channel_getter,
        state=startSG.confirm_del_channel,
    ),
    Window(
        Const('Добавленные каналы'),
        Format('{text}'),
        Column(
            SwitchTo(Const('Изменить данные'), id='choose_channel_switcher', state=startSG.choose_channel),
        ),
        SwitchTo(Const('◀️Назад'), id='back', state=startSG.start),
        getter=getters.watch_channels_getter,
        state=startSG.watch_channels
    ),
    Window(
        Const('Выберите канал для изменения'),
        Group(
            Select(
                Format('{item[0]}'),
                id='choose_channels_builder',
                item_id_getter=lambda x: x[1],
                items='items',
                on_click=getters.choose_channel_selector
            ),
            width=1
        ),
        Row(
            Button(Const('◀️'), id='back_change_channel_pager', on_click=getters.change_channels_pager, when='not_first'),
            Button(Format('{page}'), id='change_channel_pager', when='items'),
            Button(Const('▶️'), id='next_change_channel_pager', on_click=getters.change_channels_pager, when='not_last')
        ),
        SwitchTo(Const('◀️Назад'), id='back_watch_channels', state=startSG.watch_channels),
        getter=getters.choose_channel_getter,
        state=startSG.choose_channel
    ),
    Window(
        Const('Выберите пункт, который вы хотели бы изменить для канала:'),
        Format('{text}'),
        Column(
            SwitchTo(Const('Кол-во реакций'), id='change_channel_amount_switcher', state=startSG.change_channel_amount),
            SwitchTo(Const('Доп. реакции'), id='change_channel_reactions_switcher', state=startSG.change_channel_reactions),
        ),
        SwitchTo(Const('◀️Назад'), id='back_choose_channel', state=startSG.choose_channel),
        getter=getters.change_channel_menu_getter,
        state=startSG.change_channel_menu
    ),
    Window(
        Const('Введите новое количество реакций на посте'),
        TextInput(
            id='change_channel_amount',
            on_success=getters.change_channel_amount
        ),
        SwitchTo(Const('◀️Назад'), id='back_change_channel_menu', state=startSG.change_channel_menu),
        state=startSG.change_channel_amount
    ),
    Window(
        Const('Выберите новые доп. реакции для накрутки:'),
        Group(
            Multiselect(
                Format('✔️ {item[0]}'),
                Format('{item[0]}'),
                id='change_reactions_builder',
                item_id_getter=lambda x: x[1],
                items='items',
                on_click=getters.select_changed_channel_reaction,
                min_selected=1
            ),
            width=2
        ),
        Button(Const('Сохранить выбор'), id='change_channel_reactions', on_click=getters.change_channel_reactions),
        SwitchTo(Const('◀️Назад'), id='back_change_channel_menu', state=startSG.change_channel_menu),
        getter=getters.change_channel_reaction_getter,
        state=startSG.change_channel_reactions
    ),
)