import asyncio
import random
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from database.action_data_class import DataInteraction

from utils.api import create_task
from constants import SUB_REACTIONS, MAIN_REACTIONS, ADMIN_IDS


logger = logging.getLogger(__name__)


REDUCTION_PERIODS = [
    (8, 50, 8, 57),
    (10, 0, 10, 7),
    (12, 0, 12, 7),
    (15, 0, 15, 7),
    (18, 0, 18, 7),
    (20, 0, 20, 7)
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


# ИЗМЕНЕНО: get_amount больше не нужен для распределения процентов.
# Оставлен только для обратной совместимости, если где-то ещё вызывается.
def get_amount(base_amount: int, percent: float | int, task_percent: int, reduction: bool) -> int:
    base_amount = int(base_amount * percent / 100)
    amount = int(base_amount * task_percent / 100)
    if reduction:
        amount = int(amount * 0.1)  # сокращение на 90%
    return amount


def take_random(lst):
    sub_reactions = random.sample(lst, random.randint(1, len(lst)))
    random.shuffle(sub_reactions)
    return sub_reactions


async def wait_for_task(func, delay: int | float, *args):
    await asyncio.sleep(delay)
    await func(*args)


# ДОБАВЛЕНО: функция накопительного распределения.
# Принимает "сырые" реакции на задачу и список реакций с процентами.
# Возвращает словарь {reaction: amount_сейчас}.
# accumulators — общий словарь между всеми задачами, поэтому дробные части не теряются.
def distribute_amounts(task_raw: float, reactions: list[dict], accumulators: dict) -> dict:
    amounts = {}
    for reaction in reactions:
        key = reaction['reaction']
        acc = accumulators.setdefault(key, {'ideal': 0.0, 'given': 0})

        # накапливаем идеальное значение с учётом процента реакции
        acc['ideal'] += task_raw * reaction['percent'] / 100.0

        # сколько выдать СЕЙЧАС = округлённое накопленное минус уже выданное
        target = round(acc['ideal'])
        amount = target - acc['given']
        if amount < 0:
            amount = 0

        acc['given'] += amount
        amounts[key] = amount
    return amounts


# ИЗМЕНЕНО: функция теперь принимает готовый список реакций с УЖЕ рассчитанным
# количеством (amount), а не пересчитывает проценты через get_amount.
async def process_refill_task(
    channel_id: int,
    post_link: str,
    reactions: list[dict],  # каждый элемент: {'service_id': ..., 'reaction': ..., 'amount': ...}
    bot: Bot,
    session: DataInteraction
):
    channel = await session.get_channel_by_channel_id(channel_id)
    counter = 1
    failed_tasks = []
    for reaction in reactions:
        amount = reaction.get('amount', 0)
        if amount <= 0:
            # ДОБАВЛЕНО: не создаём задачи на 0 реакций — просто пропускаем
            logger.debug(f"Skip reaction {reaction.get('reaction')} with amount 0")
            counter += 1
            continue
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
        amount = reaction.get('amount', 0)
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

    # ИЗМЕНЕНО: рассчитываем доп. реакции с контролируемым рандомом (spread),
    # как в тестовой функции, вместо жёсткого деления 15 / n.
    sub_reactions_raw = take_random(list(channel.reactions))
    total_percent = 15
    spread = 0.5
    n = len(sub_reactions_raw)
    base = 1.0 / n
    weights = [base * random.uniform(1 - spread, 1 + spread) for _ in range(n)]
    weight_sum = sum(weights)
    sub_reactions = [
        {
            'service_id': SUB_REACTIONS[reaction].get('service_id'),
            'percent': round(total_percent * w / weight_sum, 2),
            'reaction': SUB_REACTIONS[reaction].get('reaction'),
        }
        for reaction, w in zip(sub_reactions_raw, weights)
    ]

    # ДОБАВЛЕНО: общий накопитель для всех задач — живёт в замыкании,
    # поэтому все asyncio-задачи, созданные ниже, делят одно состояние.
    accumulators = {}

    # ДОБАВЛЕНО: проверка конфига TASKS (сумма должна быть 100)
    tasks_percent_sum = sum(task.get('percent') for task in TASKS)
    assert abs(tasks_percent_sum - 100) < 0.01, \
        f'Сумма TASKS.percent должна быть 100, а сейчас {tasks_percent_sum}'

    is_reduction = is_reduction_period()

    if is_reduction:
        reactions = random.sample(list(MAIN_REACTIONS.copy()), 2)
    else:
        reactions = list(MAIN_REACTIONS.copy())
    random.shuffle(reactions)
    for task in TASKS:
        if len(reactions) == 3:
            main_reaction_1 = {'service_id': MAIN_REACTIONS[reactions[0]].get('service_id'), 'percent': random.randint(40, 50), 'reaction': MAIN_REACTIONS[reactions[0]].get('reaction')}
            main_reaction_2 = {'service_id': MAIN_REACTIONS[reactions[1]].get('service_id'), 'percent': random.randint(20, 30), 'reaction': MAIN_REACTIONS[reactions[1]].get('reaction')}
            reaction_percent_3 = 85 - main_reaction_1.get('percent') - main_reaction_2.get('percent')
            main_reaction_3 = {'service_id': MAIN_REACTIONS[reactions[2]].get('service_id'), 'percent': reaction_percent_3, 'reaction': MAIN_REACTIONS[reactions[2]].get('reaction')}
            main_reactions = [main_reaction_1, main_reaction_2, main_reaction_3]
        elif len(reactions) == 2:
            main_reaction_1 = {'service_id': MAIN_REACTIONS[reactions[0]].get('service_id'), 'percent': random.randint(55, 70), 'reaction': MAIN_REACTIONS[reactions[0]].get('reaction')}
            reaction_percent_2 = 85 - main_reaction_1.get('percent')
            main_reaction_2 = {'service_id': MAIN_REACTIONS[reactions[1]].get('service_id'),
                               'percent': reaction_percent_2, 'reaction': MAIN_REACTIONS[reactions[1]].get('reaction')}
            main_reactions = [main_reaction_1, main_reaction_2]
        else:
            main_reaction_1 = {'service_id': MAIN_REACTIONS[reactions[0]].get('service_id'), 'percent': 85, 'reaction': MAIN_REACTIONS[reactions[0]].get('reaction')}
            main_reactions = [main_reaction_1]

        # ДОБАВЛЕНО: собираем все реакции задачи и проверяем сумму процентов
        all_reactions = main_reactions + sub_reactions
        total_task_pct = sum(r['percent'] for r in all_reactions)
        assert abs(total_task_pct - 100) < 0.01, \
            f'Сумма процентов задачи = {total_task_pct}, а должна быть 100'

        # ИЗМЕНЕНО: считаем "сырые" реакции на задачу и распределяем накопительно.
        # task_raw — это сколько всего реакций приходится на эту задачу
        # (с учётом reduction, если сейчас период сокращения).
        task_raw = channel.amount * task.get('percent') / 100.0
        if is_reduction:
            task_raw *= 0.1  # сокращение на 90%

        # ДОБАВЛЕНО: распределяем накопительно и получаем amount для каждой реакции
        amounts = distribute_amounts(task_raw, all_reactions, accumulators)

        # ДОБАВЛЕНО: обогащаем реакции готовым amount, чтобы process_refill_task
        # не пересчитывал проценты заново (иначе снова потеряем дробные части).
        reactions_with_amount = [
            {**r, 'amount': amounts[r['reaction']]}
            for r in all_reactions
        ]

        process_task = asyncio.create_task(
            wait_for_task(
                process_refill_task,
                task.get('delay'),
                channel_id,
                post_link,
                reactions_with_amount,
                bot,
                session
            )
        )
        logger.info(f'task {process_task.get_name()} created')


def test(base_amount: int, time: datetime):
    calculate_reactions = {}
    full_amount = 0
    print(f'Начинаю создавать задание на накрутку реакций. Время: {datetime.now()}, Кол-во: {base_amount}')
    sub_reactions = ['prayer', 'hundred', 'lighting', 'cotton']
    total_percent = 15
    spread = 0.5  # максимальное отклонение от равной доли

    n = len(sub_reactions)
    base = 1.0 / n
    weights = [base * random.uniform(1 - spread, 1 + spread) for _ in range(n)]
    weight_sum = sum(weights)

    sub_reactions = [
        {
            'service_id': SUB_REACTIONS[r].get('service_id'),
            'percent': round(total_percent * w / weight_sum, 2),
            'reaction': SUB_REACTIONS[r].get('reaction'),
        }
        for r, w in zip(sub_reactions, weights)
    ]
    print('Общие задачи на доп реакции:')
    for sub_reaction in sub_reactions:
        print(f'Реакция: {sub_reaction.get("reaction")}|Процент: {sub_reaction.get("percent")}%')
    is_reduction = is_reduction_period(time)
    print('Начало создания микрозадач на время')
    counter = 1
    reactions = list(MAIN_REACTIONS.copy())
    random.shuffle(reactions)

    # ДОБАВЛЕНО: накопители для каждой реакции — живут между всеми задачами.
    # Формат: {reaction: {'ideal': float, 'given': int}}
    # 'ideal' — сколько реакция "заслужила" суммарно (дробное),
    # 'given' — сколько уже реально выдано (целое).
    accumulators = {}

    # ДОБАВЛЕНО: проверка, что сумма процентов в TASKS = 100 (защита от опечаток)
    tasks_percent_sum = sum(task.get('percent') for task in TASKS)
    assert abs(tasks_percent_sum - 100) < 0.01, \
        f'Сумма TASKS.percent должна быть 100, а сейчас {tasks_percent_sum}'

    for task in TASKS:
        print(f'Задача номер "{counter}"')
        print(f'Создание отложенной задачи на {(datetime.now() + timedelta(seconds=task.get("delay"))).time()} ({task.get("percent")}%)')
        main_reaction_1 = {'service_id': MAIN_REACTIONS[reactions[0]].get('service_id'), 'percent': random.randint(40, 50), 'reaction': MAIN_REACTIONS[reactions[0]].get('reaction')}
        main_reaction_2 = {'service_id': MAIN_REACTIONS[reactions[1]].get('service_id'), 'percent': random.randint(20, 30), 'reaction': MAIN_REACTIONS[reactions[1]].get('reaction')}
        reaction_percent_3 = 85 - main_reaction_1.get('percent') - main_reaction_2.get('percent')
        main_reaction_3 = {'service_id': MAIN_REACTIONS[reactions[2]].get('service_id'), 'percent': reaction_percent_3, 'reaction': MAIN_REACTIONS[reactions[2]].get('reaction')}
        main_reactions = [main_reaction_1, main_reaction_2, main_reaction_3]

        print('Общие задачи на основные реакции:')
        for main_reaction in main_reactions:
            print(f'Реакция: {main_reaction.get("reaction")}|Процент: {main_reaction.get("percent")}%')

        # ДОБАВЛЕНО: собираем все реакции задачи в один список
        all_reactions = main_reactions + sub_reactions

        # ДОБАВЛЕНО: проверка, что сумма процентов внутри задачи = 100
        total_task_pct = sum(r['percent'] for r in all_reactions)
        assert abs(total_task_pct - 100) < 0.01, \
            f'Сумма процентов задачи "{counter}" = {total_task_pct}, а должна быть 100'

        # ИЗМЕНЕНО: вместо get_amount для каждой реакции отдельно —
        # считаем "сырые" реакции на задачу и распределяем накопительно.
        task_raw = base_amount * task.get('percent') / 100.0

        amounts = {}
        for reaction in all_reactions:
            key = reaction['reaction']
            acc = accumulators.setdefault(key, {'ideal': 0.0, 'given': 0})

            # накапливаем идеальное значение с учётом процента реакции
            acc['ideal'] += task_raw * reaction['percent'] / 100.0

            # сколько выдать СЕЙЧАС = округлённое накопленное минус уже выданное
            target = round(acc['ideal'])
            amount = target - acc['given']
            if amount < 0:
                amount = 0  # защита на случай странных округлений

            acc['given'] += amount
            amounts[key] = amount

        print(f'Итоговые задачи на {(datetime.now() + timedelta(seconds=task.get("delay"))).time()}:')
        # ИЗМЕНЕНО: используем заранее посчитанные amounts вместо get_amount(...)
        for reaction in all_reactions:
            amount = amounts[reaction['reaction']]
            print(f'Реакция: {reaction.get("reaction")}|Кол-во: {amount}')
            full_amount += amount
            calculate_reactions[reaction['reaction']] = \
                calculate_reactions.get(reaction['reaction'], 0) + amount
        print(f'После задачи номер "{counter}" - Всего реакций: {full_amount} ({round(full_amount / base_amount, 2) * 100}%)')
        counter += 1
    print('\n\nПосле залива всех задач:')
    for reaction, amount in calculate_reactions.items():
        print(f'Реакция: {reaction} | Кол-во: {amount} ({round(amount / base_amount, 3) * 100}%)')

    # ДОБАВЛЕНО: финальная сверка — сколько всего должно было получиться
    expected_total = base_amount  # т.к. сумма TASKS.percent = 100
    print(f'\nИтого накручено: {full_amount} / {expected_total} '
          f'({round(full_amount / base_amount, 4) * 100}%)')


# test(200, datetime.now())

