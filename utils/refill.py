import asyncio
import random
import logging
from datetime import datetime

from aiogram import Bot

from database.action_data_class import DataInteraction

from utils.api import create_task
from constants import SUB_REACTIONS, MAIN_REACTIONS, ADMIN_IDS


logger = logging.getLogger(__name__)


REDUCTION_PERIODS = [
    (9, 0, 9, 7),
    (10, 0, 10, 7),
    (12, 0, 12, 7),
    (15, 0, 15, 7),
    (18, 0, 18, 7)
]


TASKS = [
    {
        'percent': 10,
        'delay': 60 * 3
    },
    {
        'percent': 10,
        'delay': 60 * 15
    },
    {
        'percent': 10,
        'delay': 60 * 40
    },
    {
        'percent': 20,
        'delay': 60 * 60 * 1.5
    },
    {
        'percent': 20,
        'delay': 60 * 60 * 3
    },
    {
        'percent': 15,
        'delay': 60 * 60 * 3.5
    },
    {
        'percent': 10,
        'delay': 60 * 60 * 4.5
    },
    {
        'percent': 5,
        'delay': 60 * 60 * 5.5
    }
]


# TASKS = [  # тестовые
#     {
#         'percent': 10,
#         'delay': 3
#     },
#     {
#         'percent': 10,
#         'delay': 15
#     },
#     {
#         'percent': 10,
#         'delay': 40
#     },
#     {
#         'percent': 20,
#         'delay': 60
#     },
#     {
#         'percent': 20,
#         'delay': 61
#     },
#     {
#         'percent': 15,
#         'delay': 61
#     },
#     {
#         'percent': 10,
#         'delay': 61
#     },
#     {
#         'percent': 5,
#         'delay': 60
#     }
# ]


def is_reduction_period(now: datetime | None = None) -> bool:
    now = datetime.now() if now is None else now
    current_minutes = now.hour * 60 + now.minute
    for start_h, start_m, end_h, end_m in REDUCTION_PERIODS:
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start <= current_minutes < end:
            return True
    return False


def get_amount(base_amount: int, percent: float | int, task_percent: int) -> int:
    base_amount = int(base_amount * percent / 100)
    amount = int(base_amount * task_percent / 100)
    if is_reduction_period():
        amount = int(amount * 0.1)  # сокращение на 90%
    return amount


def take_random(lst):
    sub_reactions = random.sample(lst, random.randint(1, len(lst)))
    random.shuffle(sub_reactions)
    return sub_reactions


async def wait_for_task(func, delay: int | float, *args):
    await asyncio.sleep(delay)
    await func(*args)


async def process_refill_task(channel_id: int, post_link: str, reactions: list[dict], percent: int, bot: Bot, session: DataInteraction):
    channel = await session.get_channel_by_channel_id(channel_id)
    counter = 1
    failed_tasks = []
    for reaction in reactions:
        amount = get_amount(channel.amount, reaction.get('percent'), percent)
        logger.info(f"{int(reaction.get('service_id'))} | {post_link} | {amount}")
        try:
            result = await create_task(
                service_id=int(reaction.get('service_id')),
                link=post_link,
                quantity=amount
            )
            logger.info(f"task ID: {int(reaction.get('service_id'))} ({reaction.get('percent')}%) created successfully")
        except Exception as err:
            failed_tasks.append(reaction)
            logger.error(f'Fail while execute "create_task": {err}')
        counter += 1
        await asyncio.sleep(1)

    if not failed_tasks:
        logger.info('Все задачи были успешно добавлены с первого раза')
        return
    logger.debug('Ошибка в процессе добавления задач')

    error = False
    for reaction in failed_tasks:
        amount = get_amount(channel.amount, reaction.get('percent'), percent)
        try:
            result = await create_task(
                service_id=int(reaction.get('service_id')),
                link=post_link,
                quantity=amount
            )
        except Exception as err:
            error = True
            logger.error(f'Критическая ошибка во время повторого выполненя задачи накрутки: {err}')
        await asyncio.sleep(1)

    if error:
        bot_channel = await bot.get_chat(channel_id)
        for telegram_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f'🚨Для канала {bot_channel.full_name} (@{bot_channel.username}) были добавленны не все задачи'
                )
            except Exception:
                ...


async def create_refill_task(channel_id: int, post_link: str, session: DataInteraction, bot: Bot):
    channel = await session.get_channel_by_channel_id(channel_id)

    sub_reactions = take_random(list(channel.reactions))
    sub_reactions = [
        {'service_id': SUB_REACTIONS[reaction].get('service_id'), 'percent': round(15 / len(list(sub_reactions)), 2)}
        for reaction in sub_reactions]
    for task in TASKS:
        reactions = list(MAIN_REACTIONS.copy())
        random.shuffle(reactions)
        main_reaction_1 = {'service_id': MAIN_REACTIONS[reactions[0]].get('service_id'), 'percent': random.randint(30, 40)}
        main_reaction_2 = {'service_id': MAIN_REACTIONS[reactions[1]].get('service_id'), 'percent': random.randint(25, 35)}
        main_reaction_3 = {'service_id': MAIN_REACTIONS[reactions[2]].get('service_id'), 'percent': 85 - random.randint(30, 40)}
        main_reactions = [main_reaction_1, main_reaction_2, main_reaction_3]

        process_task = asyncio.create_task(
            wait_for_task(
                process_refill_task,
                task.get('delay'),
                channel_id,
                post_link,
                main_reactions + sub_reactions,
                task.get('percent'),
                bot,
                session
            )
        )
        logger.info(f'task {process_task.get_name()} created')
