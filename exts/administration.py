import discord
from discord.ext import commands, tasks
from discord.utils import get
import asyncio


async def create_mute_role(guild: discord.Guild):
    perms = discord.Permissions.none()
    newrole = await guild.create_role(name="Muted", permissions=perms)

    ow = discord.PermissionOverwrite(send_messages=False, add_reactions=False)

    for channel in guild.channels:
        await channel.set_permissions(newrole, overwrite=ow)

    return newrole

QUERY_INTERVAL_MINUTES = 30


def parsetime(time: str):
    arr = time.split(' ')
    hours = 0
    minutes = 0
    for elem in arr:
        if elem.endswith('h'):
            hours += int(elem[0:len(elem)-1])
        elif elem.endswith('m'):
            minutes += int(elem[0:len(elem) - 1])
    return {'hours': hours, 'minutes': minutes}


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

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def mute(self, ctx, target: discord.Member, time: str = None):
        mr = get(ctx.guild.roles, name="Muted")
        if not mr:
            await ctx.send("Server doesn't seem to have mute configured yet, stand by please.")
            async with ctx.channel.typing():
                mr = await create_mute_role(ctx.guild)

        if not time:
            await target.add_roles(mr)
            e = discord.Embed(description=f"{target} has been muted")
            e1 = discord.Embed(description=f"You have been muted from the server {ctx.guild} indefinitely, you'll only"
                                           f"be able to send messages if a moderator unmutes you")
            await ctx.send(embed=e)
            await target.send(embed=e1)

        if time:
            pass

    @tasks.loop(minutes=QUERY_INTERVAL_MINUTES)
    async def mute_poll(self):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                async for entry in conn.cursor("SELECT "):
                    pass


def setup(bot: commands.Bot):
    bot.add_cog(administration(bot))
