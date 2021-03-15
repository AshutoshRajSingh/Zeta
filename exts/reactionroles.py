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
        role: discord.Role = await self.check_payload(payload)

        if role:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Does the same thing as the one above it excepts removes a role from the user who unreacted from message
        """
        role: discord.Role = await self.check_payload(payload)

        if role:
            guild = self.bot.get_guild(payload.guild_id)
            member: discord.Member = guild.get_member(payload.user_id)
            await member.remove_roles(role)

    @commands.group()
    async def reacrole(self, ctx: commands.Context):
        pass

    @reacrole.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def create(self, ctx: commands.Context, title: str, *roles: discord.Role):
        brake = {}

        def check(_r, _u):
            return _u == ctx.author and _r.message == me

        me = await ctx.send(f'React with the reaction that will correspond to the role `{roles[0]}`')

        # Yes I know this is an ugly solution to avoid an unnecessary api request but it it ultimately the only solution
        # I could think of.
        try:
            r, u = await self.bot.wait_for('reaction_add', timeout=len(roles) * 20, check=check)
            brake[str(r.emoji)] = roles[0].id
        except asyncio.TimeoutError:
            await ctx.send("Timed out, please run the command again and this time be a little quicker to react.")
            return

        try:
            for role in roles[1:]:
                await me.edit(content=f'React with the reaction that will correspond to the role `{role}`')
                r, u = await self.bot.wait_for('reaction_add', timeout=len(roles) * 20, check=check)
                brake[str(r.emoji)] = role.id
        except asyncio.TimeoutError:
            await ctx.send('Timed out, please run the command again and this time be a little quicker to react.')
            return

        await ctx.send(
            'What channel do you wish to send this role menu in? Enter its id, name or mention it: #<channel>')

        for count in range(4):
            try:
                m = await self.bot.wait_for('message', check=lambda _m: _m.author == ctx.author, timeout=30)
                chan = await self.tcc.convert(ctx, m.content)
                break
            except commands.BadArgument:
                if count == 3:
                    await ctx.send("Too many tries to enter channel, make sure I can actually see the channel you're "
                                   "referring to and use the entire command again")
                    return
                await ctx.send("Please enter the correct channel, if in doubt, try mentioning it, the `#channel` thing")
            except asyncio.TimeoutError:
                await ctx.send("Timed out")
                return
        outstring = ""
        for k, v in brake.items():
            outstring += f'{k} - {ctx.guild.get_role(v)}\n\n'

        e = discord.Embed(title=f"Role menu: {title}",
                          description=outstring,
                          colour=discord.Colour.blue())

        zero = await chan.send(embed=e)

        for k in brake:
            await zero.add_reaction(k)

        self._cache[ctx.guild.id][zero.id] = brake

        for k, v in brake.items():
            await self.bot.pool.execute(
                'INSERT INTO selfrole (guildid, roleid, messageid, emoji) VALUES($1, $2, $3, $4)',
                ctx.guild.id, v, zero.id, k)


def setup(bot: commands.Bot):
    bot.add_cog(ReactionRoles(bot))
