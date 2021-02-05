import discord
from discord.ext import commands
import asyncio


class administration(commands.Cog):
    """
    Class that implements administration commands for a guild
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self._cache = {}

        # asyncio.get_event_loop().create_task(self.load_cache())

    async def load_cache(self):
        """Loads cache for moderative actions, not in use currently but future plans involve this as requirement"""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            self._cache[guild.id] = {}

    # ------------------------------------Moderative actions--------------------------------------------

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx: commands.Context):
        await ctx.guild.default_role.edit(permissions=discord.Permissions(send_messages=False, add_reactions=False))
        await ctx.send(
            embed=discord.Embed(title="A server-wide lockdown is now in effect", colour=discord.Colour.red()))

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def unlock(self, ctx: commands.Context):
        await ctx.guild.default_role.edit(permissions=discord.Permissions.general())
        await ctx.send(
            embed=discord.Embed(title="Lockdown lifted", colour=discord.Colour.green()))


def setup(bot: commands.Bot):
    bot.add_cog(administration(bot))
