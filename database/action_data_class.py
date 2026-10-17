import datetime

from sqlalchemy import select, insert, update, column, text, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.model import (ChannelsTable)


class DataInteraction():
    def __init__(self, session: async_sessionmaker):
        self._sessions = session

    async def add_channel(self, channel_id: int, name: str, reactions: list[str], amount: int):
        async with self._sessions() as session:
            await session.execute(insert(ChannelsTable).values(
                channel_id=channel_id,
                name=name,
                reactions=reactions,
                amount=amount
            ))
            await session.commit()

    async def get_channels(self):
        async with self._sessions() as session:
            result = await session.scalars(select(ChannelsTable))
        return result.fetchall()

    async def get_channel_by_channel_id(self, channel_id: int):
        async with self._sessions() as session:
            result = await session.scalar(select(ChannelsTable).where(ChannelsTable.channel_id == channel_id))
        return result

    async def get_channel_by_uid(self, id: int):
        async with self._sessions() as session:
            result = await session.scalar(select(ChannelsTable).where(ChannelsTable.id == id))
        return result

    async def set_channel_value(self, id: int, column: str, value: any):
        async with self._sessions() as session:
            await session.execute(update(ChannelsTable).where(ChannelsTable.id == id).values(
                {
                    column: value
                }
            ))
            await session.commit()

    async def del_channel(self, id: int):
        async with self._sessions() as session:
            await session.execute(delete(ChannelsTable).where(ChannelsTable.id == id))
            await session.commit()


