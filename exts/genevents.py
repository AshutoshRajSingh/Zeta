import discord
import datetime
from discord.ext import commands


class GenEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
        Listens for guild joining and then makes database entry
        """
        await self.bot.db.make_guild_entry(guild.id)
        await self.bot.db.create_member_table(guild=guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        Yank out the guild from the database when bot leaves it
        """
        await self.bot.db.hakai_guild(guild.id)

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Called every time a ready event is received, we only need the first time to mark initial readying
        """
        if not self.bot.initinit:
            print(f"First READY dispatched at {datetime.datetime.utcnow()}")
            self.bot.initinit = True

    @commands.Cog.listener('on_message')
    async def ping_reminder(self, message: discord.Message):
        """
        If bot is pinged a help message telling about command prefix for that server is shown
        """
        if message.guild.me in message.mentions:
            prefix = self.bot.prefixes.get(message.guild.id)
            if prefix:
                pass
            else:
                prefix = '.'
            await message.channel.send(f"Did you forget my prefix? For this server, it is `{prefix}`\n"
                                       f"Use `{prefix}help` for more information!\n"
                                       f"Hint: Admins can change the server prefix using the `prefix` command")


def setup(bot: commands.Bot):
    bot.add_cog(GenEvents(bot))
