from dataclasses import dataclass

from environs import Env

'''
    При необходимости конфиг базы данных или других сторонних сервисов
'''


@dataclass
class SexySMM:
    api_key: str


@dataclass
class tg_bot:
    token: str


@dataclass
class DB:
    dns: str


@dataclass
class Config:
    bot: tg_bot
    db: DB
    sexysmm: SexySMM


def load_config(path: str | None = None) -> Config:
    env: Env = Env()
    env.read_env(path)

    return Config(
        bot=tg_bot(
            token=env('token')
        ),
        db=DB(
            dns=env('dns')
        ),
        sexysmm=SexySMM(
            api_key=env('sexysmm_api_key')
        )
    )
