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

        asyncio.get_event_loop().create_task(self.load_cache())

    async def get_lockdown_ignored_channel_ids(self, guildid: int):
        if type(guildid) is not int:
            raise ValueError("guildid must be int")

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                async for entry in conn.cursor("SELECT id, lockic FROM guilds WHERE id = $1", guildid):
                    data = entry.get('lockic')
                    return data

    async def load_cache(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            self._cache[guild.id] = {}
            self._cache[guild.id]['lockic'] = await self.get_lockdown_ignored_channel_ids(guild.id)
            print(f'cache loaded for guild id {guild.id}')

    # ------------------------------------Moderative actions--------------------------------------------

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx: commands.Context):
        ignored_channels = self._cache[ctx.guild.id]['lockic']

        if not ignored_channels:
            ignored_channels = []

        overwrite = discord.PermissionOverwrite(send_messages=False, add_reactions=False)

        async with ctx.channel.typing():
            for channel in ctx.guild.channels:
                if channel.id not in ignored_channels:
                    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

            embed = discord.Embed(title="Lockdown in effect")
            await ctx.send(embed=embed)

    @commands.command(aliases=['lics', 'lockic'])
    @commands.has_guild_permissions(administrator=True)
    async def lockdownignoredchannels(self, ctx: commands.Context):
        channels = self._cache[ctx.guild.id]['lockic']

        description = ""

        if channels:
            title = "Following channels will be ignored in the event of lockdown"
            for chan_id in channels:
                if ctx.guild.get_channel(chan_id):
                    description += f"{ctx.guild.get_channel(chan_id).mention}\n"
        else:
            title = f"This server has no channels set to be ignored during lockdown, use `{ctx.prefix}lockignore` to " \
                    f"add channels to be ignored."

        await ctx.send(embed=discord.Embed(title=title, description=description))

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def lockignore(self, ctx: commands.Context, target_channel: discord.TextChannel):
        async with self.bot.pool.acquire() as conn:
            chanlist = self._cache[ctx.guild.id].get('lockic')

            if not chanlist:
                self._cache[ctx.guild.id]['lockic'] = [target_channel.id]
            else:
                self._cache[ctx.guild.id]['lockic'].append(target_channel.id)

            await conn.execute("UPDATE guilds SET lockic = $1 WHERE id = $2",
                               self._cache[ctx.guild.id]['lockic'],
                               ctx.guild.id)

            await ctx.send(embed=discord.Embed(description=f"{target_channel.mention} will be ignored on lockdown",
                                               colour=discord.Colour.blue()))


def setup(bot: commands.Bot):
    bot.add_cog(administration(bot))
