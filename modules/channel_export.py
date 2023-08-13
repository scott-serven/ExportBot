import discord
from discord.ext import commands, tasks

import core
from modules.exporter.channel_exporter import ChannelExporter


try:
    from .core import *
except ImportError:
    from core import *


class ExportCommand:
    def __init__(self, export_channel_id: int, output_channel_id: int):
        self.export_channel_id = export_channel_id
        self.output_channel_id = output_channel_id


class ChannelExport(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.current_export_command: ExportCommand | None = None
        self.export_queue: list[ExportCommand] = []
        self.check_export_queue.start()

    async def backup_channel(self, export_command: ExportCommand) -> None:
        channel: discord.TextChannel = self.bot.get_channel(export_command.export_channel_id)
        channel_exporter = ChannelExporter(
            self.bot, channel, f"output/{export_command.export_channel_id}", export_command.output_channel_id
        )
        await channel_exporter.export()

    @commands.command()
    @commands.has_role(core.config["EXPORT"]["role"])
    async def export(self, ctx: commands.Context, export_channel_id: int, output_channel_id: int = -1):
        self.export_queue.append(ExportCommand(export_channel_id, output_channel_id))

    @commands.command()
    @commands.has_role(core.config["EXPORT"]["role"])
    async def debug(self, ctx: commands.Context, export_channel_id: int, export_message_id: int):
        channel: discord.TextChannel = self.bot.get_channel(export_channel_id)
        channel_exporter = ChannelExporter(self.bot, channel, f"output/debug", ctx.channel.id)
        await channel_exporter.debug(export_message_id)

    @tasks.loop(seconds=1)
    async def check_export_queue(self):
        # only allow one backup at a time to minimize rate limiting
        if self.current_export_command is None and len(self.export_queue) > 0:
            self.current_export_command = self.export_queue.pop()
            try:
                await self.backup_channel(self.current_export_command)
            finally:
                self.current_export_command = None


async def setup(bot: Bot) -> None:
    await bot.add_cog(ChannelExport(bot))
