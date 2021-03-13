import asyncio
import discord
from discord.ext import commands
from discord.ext.commands import TextChannelConverter


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cache = {}
        self.tcc = TextChannelConverter()
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            self._cache[guild.id] = await self.bot.db.fetch_guild_selfole_data(guild.id)

    async def check_payload(self, payload: discord.RawReactionActionEvent):
        """
        Checks the payload against internal cache, if a preconfigured reaction roles message and emoji are detected,
        returns the discord.Role object corresponding to it.
        Args:
            payload: discord.RawReactionActionEvent

        Returns:
            Optional[discord.Role]
        """
        guild = self.bot.get_guild(payload.guild_id)
        emoji = payload.emoji

        """
        Cache implementation:
        {
            guild_id: {
                message_id: {
                    emoji: roleid
                    }
                }
            }
        }    
        """

        if guild.id in self._cache:
            if payload.message_id in self._cache[guild.id]:
                if str(emoji) in self._cache[guild.id][payload.message_id]:
                    return guild.get_role(self._cache[guild.id][payload.message_id][str(emoji)])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Listener that takes care of assigning a role to a member based off their adding reaction
        Cog maintains an internal cache containing information about what reaction from what message from w
        hat guild corresponds to what role to be assigned
        """
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)

        role = await self.check_payload(payload)

        if role:
            await member.add_roles(role)
        else:
            pass

    @commands.group()
    async def reacrole(self, ctx: commands.Context):
        pass

    @reacrole.command()
    async def create(self, ctx: commands.Context, *roles: discord.Role):
        brake = {}

        def check(_r, _u):
            return _u == ctx.author and _r.message == me

        me = await ctx.send(f'React with the reaction that will correspond to the role {roles[0]}')

        try:
            for role in roles:
                await me.edit(content=f'React with the reaction that will correspond to the role {role}')
                r, u = await self.bot.wait_for('reaction_add', timeout=len(roles)*20, check=check)
                brake[str(r.emoji)] = role.id
        except asyncio.TimeoutError:
            await ctx.send('timed out')
            return

        await ctx.send('send id of channel to send menu in')
        m = await self.bot.wait_for('message', check=lambda _m: _m.author == ctx.author, timeout=30)

        chan = await self.tcc.convert(ctx, m.content)

        outstring = "Role menu\n"
        for k, v in brake.items():
            outstring += f'{k} - {ctx.guild.get_role(v)}\n'

        zero = await chan.send(outstring)
        self._cache[ctx.guild.id][zero.id] = brake

        for k, v in brake.items():
            await self.bot.pool.execute('INSERT INTO selfrole (guildid, roleid, messageid, emoji) VALUES($1, $2, $3, $4)',
                                        ctx.guild.id, v, zero.id, k)


def setup(bot: commands.Bot):
    bot.add_cog(ReactionRoles(bot))
