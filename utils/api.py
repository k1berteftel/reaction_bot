import asyncio
import aiohttp
import logging

from errors import ApiRequestError
from config_data.config import Config, load_config
from cachetools import TTLCache


config: Config = load_config()


BASE_URL = 'https://sexy-smm.ru/api/index.php'

cache = TTLCache(
    maxsize=1000,
    ttl=60 * 3
)
logger = logging.getLogger(__name__)


async def create_task(service_id: int, link: str, quantity: int) -> int:
    """
    Возвращает ID заказа типа int
    """
    logger.info(f"input params: {service_id}, {link}, {quantity}")
    params = {
        'r': 'v1/order/create',
        'key': config.sexysmm.api_key,
        'service': str(service_id),
        'link': link,
        'quantity': quantity
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            logger.info('send request')
            if response.status not in [200, 201]:
                try:
                    err_text = await response.json()
                except Exception:
                    err_text = await response.text()
                error = ApiRequestError.TEXT.format(err=err_text)
                logger.error(error)
                raise ApiRequestError
            data = await response.json()
    return int(data.get('order', 1))


# print(asyncio.run(create_task(350, 'https://t.me/reacrive_testing/17', 2)))


async def get_account_balance() -> float:
    """
    Возвращает баланс аккаунт типа float
    """
    params = {
        'r': 'v1/user/balance',
        'key': config.sexysmm.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status not in [200, 201]:
                try:
                    err_text = await response.json()
                except Exception:
                    err_text = await response.text()
                error = ApiRequestError.TEXT.format(err=err_text)
                logger.error(error)
                raise ApiRequestError
            data = await response.json()
    return float(data.get('balance'))


async def testing():
    params = {
        'r': 'v1/service/index',
        'key': config.sexysmm.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            print(response.status)
            data = await response.json()
            for service in data:
                print(service, sep=' ')
#
asyncio.run(testing())


"""
Основа:
{'service': 268, 'name': 'Реакции на пост (🔥)', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}
{'service': 145, 'name': 'Реакция на пост (❤️) ', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}
{'service': 240, 'name': 'Реакции на пост (👍)', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}

Доп:
{'service': 453, 'name': 'Реакции на пост (❤️\u200d🔥)', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}
{'service': 454, 'name': 'Реакции на пост (🙏)', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}
{'service': 455, 'name': ' Реакции на пост (💯) ', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}
{'service': 456, 'name': 'Реакции на пост (✍️)', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}
{'service': 457, 'name': 'Реакции на пост (👏)', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}
{'service': 350, 'name': 'Реакции на пост (⚡️)', 'category': 'Telegram', 'group': 'Реакции', 'rate': 0.002, 'min': 1, 'max': 10000}
"""
