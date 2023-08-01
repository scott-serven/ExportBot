from typing import Literal, TypedDict


class TOKENS(TypedDict):
    bot: str
    tbot: str


class LOGGING(TypedDict):
    level: Literal[10, 20, 30, 40, 50]


class BOT(TypedDict):
    prefix: str


class TBOT(TypedDict):
    prefix: str
    channels: list[str]


class Config(TypedDict):
    TOKENS: TOKENS
    LOGGING: LOGGING
    BOT: BOT
    TBOT: TBOT
