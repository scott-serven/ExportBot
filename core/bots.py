"""
MIT License

Copyright (c) 2023 TimeEnjoyed, EvieePy(MystyPy)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import logging
import pathlib

import discord
from discord.ext import commands
from twitchio.ext import commands as tcommands

from .config import config


logger: logging.Logger = logging.getLogger(__name__)


__all__ = ("Bot", "TBot")


class Bot(commands.Bot):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(command_prefix=config["BOT"]["prefix"], intents=intents, case_insensitive=True)

    async def on_ready(self) -> None:
        logger.info(f"Logged into Discord as: {self.user} | {self.user.id}")
        print("on_ready")

    async def setup_hook(self) -> None:
        print("setup_hook")
        modules: list[str] = [f'{p.parent}.{p.stem}' for p in pathlib.Path('modules').glob('*.py')]
        modules: list[str] = [s.replace('/', '.').replace('\\', '.') for s in modules]
        print("modules", modules)
        for module in modules:
            await self.load_extension(module)

class TBot(tcommands.Bot):
    def __init__(self) -> None:
        super().__init__(
            token=config["TOKENS"]["tbot"], prefix=config["TBOT"]["prefix"], initial_channels=config["TBOT"]["channels"]
        )

    async def event_ready(self) -> None:
        logger.info(f"Logged into Twitch as: {self.nick}")
