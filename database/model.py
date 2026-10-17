import datetime

from sqlalchemy import BigInteger, VARCHAR, ForeignKey, DateTime, Boolean, Column, Integer, String, func, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class ChannelsTable(Base):
    __tablename__ = 'channels'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    channel_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(VARCHAR)
    amount: Mapped[int] = mapped_column(Integer)
    reactions: Mapped[list[str]] = mapped_column(ARRAY(VARCHAR))

    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=func.now())
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=func.now())


