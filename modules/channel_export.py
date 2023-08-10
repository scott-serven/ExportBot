import discord
from discord.ext import tasks, commands
from modules.exporter.channel_exporter import ChannelExporter

try:
    from .core import *
except ImportError:
    from core import *


class ChannelExport(commands.Cog):

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.current_backup_channel_id: int | None = None
        self.backup_queue: list[int] = []
        self.check_backup_queue.start()

    async def backup_channel(self, channel_id: int) -> None:
        channel: discord.TextChannel = self.bot.get_channel(channel_id)
        channel_exporter = ChannelExporter(self.bot, channel, f'output/{channel_id}')
        await channel_exporter.export()

    @commands.command()
    @commands.is_owner()
    async def export(self, ctx: commands.Context, channel_id: int):
        self.backup_queue.append(channel_id)
        await ctx.send(f"Channel {ctx.channel.name} backup is queued.  A message / zip file will be posted to the target channel when complete")

    @tasks.loop(seconds=1)
    async def check_backup_queue(self):
        # only allow one backup at a time to minimize rate limiting
        if self.current_backup_channel_id is None and len(self.backup_queue) > 0:
            self.current_backup_channel_id = self.backup_queue.pop()
            try:
                await self.backup_channel(self.current_backup_channel_id)
            finally:
                self.current_backup_channel_id = None


async def setup(bot: Bot) -> None:
    await bot.add_cog(ChannelExport(bot))

