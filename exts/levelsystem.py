import asyncio
import discord
import datetime
from main import Zeta
from typing import Union
from math import floor, sqrt
from discord.ext import commands, tasks


def is_me(ctx):
    return ctx.author.id == 501451372147769355


QUERY_INTERVAL_MINUTES = 10


class LevelSystem(commands.Cog, name="Levelling"):
    """
    Commands related to levelling, as you send messages, you receive exp points which translate to different levels.
    """

    def __init__(self, bot: Zeta):
        super().__init__()
        self.bot = bot

        # Look up implementation inside the add_to_cache function docstring
        self._cache = {}
        asyncio.get_event_loop().create_task(self.load_cache())

        # Start the loop that dumps cache to database every 10 minutes
        self.update_level_db.start()

    async def cog_check(self, ctx: commands.Context):
        try:
            return self.bot.guild_prefs[ctx.guild.id]['levelling']
        except KeyError:
            return False

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            if ctx.guild.id not in self.bot.guild_prefs:
                cg = self.bot.get_cog('Configuration')
                await cg.create_default_guild_prefs(ctx.guild.id)
            if not self.bot.guild_prefs[ctx.guild.id].get('levelling'):
                await ctx.send("The `levelling` plugin has been disabled on this server therefore related commands will not work\n"
                               "Hint: Server admins can enable it using the `plugin enable` command, use the help command to learn more.")

    async def load_cache(self):
        for guild in self.bot.guilds:
            self._cache[guild.id] = {}

    async def give_exp(self, guild_id: int, member_id: int, amount=None) -> None:
        """
        Function to give exp to a particular member

        Parameters:
        :param guild_id: The id of the guild in question
        :param member_id: The id of the member in the guild
        :param amount: The amount of exp to give, default to None in which case the default level up exp is awarded
        :return: None
        """
        if member_id not in self._cache[guild_id]:
            await self.add_to_cache(guild_id, member_id)

        if not amount:
            amount = 5 * self._cache[guild_id][member_id]['boost']
        self._cache[guild_id][member_id]['exp'] += amount

    async def add_to_cache(self, guild_id: int, member_id: int) -> Union[dict, None]:
        """
        Function that adds a member to the cache

        Cache: \n
            type = dict \n
            format: \n
            {
                guild_id : {
                    member_id : {
                        'id' : "the id of the member",\n
                        'level' : "the level of the member",\n
                        'exp' : "the exp of the member", \n
                        'boost' : "the boost multiplier", \n

                    }
                }
            }

        :param guild_id: the id of the guild
        :param member_id: the id of the member belonging to that guild
        :return: data(dict) - The member that was just put inside db, same format as cache.
        """
        if guild_id in self._cache and member_id in self._cache[guild_id]:
            pass

        if type(guild_id) is not int:
            raise TypeError("guild id must be int")

        data = await self.bot.db.fetch_member(guild_id, member_id)

        if data:
            self._cache[guild_id][member_id] = {
                'id': data.get('id'),
                'level': data.get('level'),
                'exp': data.get('exp'),
                'boost': data.get('boost'),
            }
        else:
            await self.add_to_db(guild_id, member_id)
            await self.add_to_cache(guild_id, member_id)  # important
        return data

    async def add_to_db(self, guild_id: int, member_id: int) -> None:
        """
        A function that adds a new entry to the database with default values

        (and not dump existing cache into database)

        :param guild_id: The relevant guild
        :param member_id: The id of the member
        :return: None
        """
        await self.bot.db.make_member_entry(guild_id, member_id)

    async def dump_single_guild(self, guildid: int):
        """
        Function that dumps all entries from a single guild in the cache to the database.

        :param guildid: the id of the guild whose cache entry needs to be dumped
        :return: None
        """
        data = self._cache[guildid]
        for memberid in list(data):
            current = data[memberid]
            query = f"UPDATE server_members " \
                    f"SET level = $1, " \
                    f"exp = $2, " \
                    f"boost = $3" \
                    f"WHERE memberid = $4 AND guildid = $5"

            await self.bot.pool.execute(query,
                                        current['level'],
                                        current['exp'],
                                        current['boost'],
                                        memberid, guildid)

    async def fetch_top_n(self, guild: discord.Guild, limit: int):
        """
        Function to fetch top n members of a guild based off exp, works by initially dumping the guild into the database
        then using an sql query to fetch the top n members

        :param guild: the guild in question
        :param limit: the number of members to fetch
        :return: None
        """

        if guild.id in self._cache:
            await self.dump_single_guild(guild.id)

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                top10 = []
                rank = 1
                async for entry in conn.cursor("SELECT memberid, exp, level FROM server_members WHERE guildid = $1 ORDER BY exp DESC LIMIT $2", guild.id, limit):
                    top10 += [{'rank': rank, 'id': entry.get('memberid'), 'exp': entry.get('exp'), 'level': entry.get('level')}]
                    rank += 1
                return top10

    @tasks.loop(minutes=QUERY_INTERVAL_MINUTES)
    async def update_level_db(self):
        """
        Loop that dumps the cache into db every 10 minutes

        :return: None
        """
        for guildId in self._cache:
            await self.dump_single_guild(guildId)
            self._cache[guildId] = {}
        print(f"Level system database updated at {datetime.datetime.utcnow()}")

    @update_level_db.before_loop
    async def preloop(self) -> None:
        """
        using this neat little feature in the library you can make sure the cache is ready before the loop starts
        """
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        The listener that takes care of awarding exp, levelling up the members

        :param message: the discord.Message object
        :return: None
        """
        try:
            if self.bot.guild_prefs[message.guild.id] is None:
                await self.bot.get_cog('Configuration').create_default_guild_prefs(message.guild.id)
                return
            elif not self.bot.guild_prefs[message.guild.id].get('levelling'):
                return
        except KeyError:
            await self.bot.get_cog('Configuration').create_default_guild_prefs(message.guild.id)
            return

        # Bots shouldn't be levelling up
        if not message.author.bot:
            # This bit awards exp points
            if message.guild.id not in self._cache:
                self._cache[message.guild.id] = {}
                await self.add_to_cache(message.guild.id, message.author.id)
            if message.author.id not in self._cache[message.guild.id]:
                await self.add_to_cache(message.guild.id, message.author.id)
            await self.give_exp(message.guild.id, message.author.id)

            # This bit checks if level up happened
            OldLevel = self._cache[message.guild.id][message.author.id]['level']
            NewLevel = floor((25 + sqrt(625 + 100 * self._cache[message.guild.id][message.author.id]['exp'])) / 50)
            if NewLevel > OldLevel:
                self._cache[message.guild.id][message.author.id]['level'] = NewLevel
                embed = discord.Embed(title=f"{message.author}",
                                      description=f"GZ on level {NewLevel}, {message.author.mention}",
                                      color=discord.Colour.green())
                await message.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        self._cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        self._cache[member.guild.id].pop(member.id)
        await self.bot.db.hakai_member(member.guild.id, member.id)

    @commands.command()
    async def level(self, ctx: commands.Context, target: discord.Member = None):
        """
        Used to show own or someone else's level

        `target` here is the member whose level you wish to know (can be mention, id or username), if no target specified, own level is shown.
        """
        if not target:
            target = ctx.author
        if ctx.guild.id in self._cache and target.id in self._cache[ctx.guild.id]:
            data = self._cache[ctx.guild.id][target.id]
        else:
            data = await self.add_to_cache(ctx.guild.id, target.id)
        if not data:
            await ctx.send(f"{target} hasn't been ranked yet! tell them to send some messages to start.")
            return
        embed = discord.Embed(title=f"{target}",
                              description=f"You are currently on level : {data['level']}\n"
                                          f"With exp : {data['exp']}",
                              colour=discord.Colour.blue())
        await ctx.send(embed=embed)

    @commands.command()
    async def lb(self, ctx):
        """
        Shows the top 10 server members based off their exp.
        """
        data = await self.fetch_top_n(ctx.guild, limit=10)

        embed = discord.Embed(title="Server leaderboard",
                              colour=discord.Colour.green())
        for entry in data:
            m = ctx.guild.get_member(entry.get('id'))
            if m is None:
                display_name = f"Deleted user (id:{entry.get('id')})"
                embed.set_footer(text="Hint: mods can use the reset command to get rid of the \"Deleted user\" in the leaderboard if they have left the server")
            else:
                display_name = m.display_name
            embed.add_field(name=f"{entry.get('rank')}.{display_name}",
                            value=f"Level: {entry.get('level')} Exp: {entry.get('exp')}",
                            inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def setmultiplier(self, ctx: commands.Context, target: discord.Member, multiplier: int):
        """
        Used to set exp multiplier of a member

        Note that you need to have the server permisson "Manage messages" in order to use this command

        `target` here is the member whose multiplier you wish to set, can be mention, id or username
        `multiplier` here is the exp multiplier you want to set, a value of 2 will indicate twice as fast levelling
        """
        if target.id not in self._cache[ctx.guild.id]:
            await self.add_to_cache(ctx.guild.id, target.id)
        self._cache[ctx.guild.id][target.id]['boost'] = int(multiplier)
        await ctx.send(f"{target}'s multiplier has been set to {multiplier}")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def giveexp(self, ctx: commands.Context, target: discord.Member, amount: int):
        """
        Used to award a certain amount of exp to a member

        Note that you need to have the server permission "manage_messages" to use this command

        `target` here is the member who you wish to give exp points to
        `amount` is the number of exp points you wish to award that member
        """
        await self.give_exp(ctx.guild.id, target.id, amount=int(amount))
        e = discord.Embed(title="Success",
                          description=f"Added {amount} points to {target.mention}",
                          colour=discord.Colour.green())
        await ctx.send(embed=e)

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def reset(self, ctx: commands.Context, target: Union[discord.Member, int]):
        """
        Resets a member's exp/level and basically removes them from the database.

        This is useful in the event that a member leaves the guild when the bot is offline therefore it is not able to automatically delete their entry so it shows up as `deleted user` on the leaderboard
        `target` here is the member you'd like to reset, can be id or mention
        """
        if type(target) is int:
            pass
        else:
            target = target.id

        try:
            self._cache[ctx.guild.id].pop(target)
        except KeyError:
            pass
        finally:
            await self.bot.db.hakai_member(ctx.guild.id, target)

    @commands.command(hidden=True)
    @commands.check(is_me)
    async def update_db(self, ctx):
        """
        Command to update the database manually, mostly used for testing purposes, or when planning to take bot down
        for maintenance
        """
        await self.update_level_db()
        await ctx.send("db updated (hopefully)")


def setup(bot: Zeta):
    bot.add_cog(LevelSystem(bot))
