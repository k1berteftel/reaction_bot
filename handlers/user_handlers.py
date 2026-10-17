from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from utils.refill import create_refill_task
from database.action_data_class import DataInteraction
from states.state_groups import startSG


user_router = Router()


@user_router.message(CommandStart())
async def start_dialog(msg: Message, dialog_manager: DialogManager, session: DataInteraction, command: CommandObject):
    if dialog_manager.has_context():
        await dialog_manager.done()
        try:
            await msg.bot.delete_message(chat_id=msg.from_user.id, message_id=msg.message_id - 1)
        except Exception:
            ...
    await dialog_manager.start(state=startSG.start, mode=StartMode.RESET_STACK)


@user_router.channel_post()
async def handle_channel_post(msg: Message, session: DataInteraction, **kwargs):
    channel = await session.get_channel_by_channel_id(msg.chat.id)
    if not channel:
        return
    post_link = msg.get_url()
    await create_refill_task(
        channel_id=msg.chat.id,
        post_link=post_link,
        session=session,
        bot=msg.bot
    )

