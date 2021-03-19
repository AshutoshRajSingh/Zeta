import sys
import time
import discord
import asyncpg
import datetime
from discord.ext import commands

start = datetime.datetime.utcnow()


class Misc(commands.Cog):
    """
    Miscellaneous commands that don't quite fit any other category
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_privileged_intents(self):
        retval = ""
        if self.bot.intents.members:
            retval += "members\n"
        if self.bot.intents.presences:
            retval += "presences\n"
        return retval

    @commands.command()
    async def info(self, ctx: commands.Context):
        """
        Sends info about the bot, you gotta use it to see.
        """
        e = discord.Embed(title=f"{self.bot.user.name}",
                          description=f"A big dumdum discord bot made by {self.bot.get_user(501451372147769355)}",
                          colour=discord.Colour.blue())

        # Calculate uptime
        uptime = datetime.datetime.utcnow() - start
        hours = int(uptime.seconds / 3600)
        mins = (uptime.seconds // 60) % 60
        secs = uptime.seconds - (hours * 3600 + mins * 60)
        e.add_field(name="Uptime", value=f"{hours}:{mins}:{secs}")

        e.add_field(name="Websocket latency", value=f"{int(self.bot.latency * 1000)}ms")

        # Calculate database latency
        temp_start = time.time()
        await self.bot.pool.execute('select')
        e.add_field(name="Database latency", value=f"{int((time.time() - temp_start) * 1000)}ms")

        e.add_field(name="Servers joined", value=len(self.bot.guilds))
        e.add_field(name="Users watched", value=len(self.bot.users))
        e.add_field(name="Privileged Intents", value=self.get_privileged_intents())
        e.add_field(name="Python version", value=f"{sys.version[:5]}")
        e.add_field(name="discord.py version", value=f"{discord.__version__}")
        e.add_field(name="asyncpg version", value=f"{asyncpg.__version__}")
        await ctx.send(embed=e)

    @commands.command()
    async def invite(self, ctx: commands.Context):
        """
        Sends a link to add me to a server.
        """
        INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=768171284810694687&permissions=2080763095&scope=bot"
        e = discord.Embed(description=f"Click [here]({INVITE_URL}) to add me to your server!",
                          colour=discord.Colour(0xFFB6C1))
        await ctx.send(embed=e)

    @commands.command()
    async def source(self, ctx: commands.Context):
        """
        Sends github link to source code
        """
        await ctx.send(embed=discord.Embed(description="[Github](https://github.com/finite-simple-group-of-order-two/Zeta)",
                                           colour=discord.Colour(0xFFB6C1)))


def setup(bot: commands.Bot):
    bot.add_cog(Misc(bot))

