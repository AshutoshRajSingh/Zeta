import discord
from discord.ext import commands, tasks
from math import floor, sqrt
from typing import Union
import asyncio


def is_me(ctx):
    return ctx.author.id == 501451372147769355


class LevelSystem(commands.Cog):
    """
    A Cog that implements a level system for messaging on multiple discord servers.\n
    Attributes:
        bot : the bot instance
        _cache: protected cache attribute for rapid short term storage of the data, dumped into db every 10 minutes
    Functions:
        await give_exp(guild_id, member_id, amount=None) : give exp to a member\n

        await add_to_cache(guild_id, member_id) : add a member to cache\n

        await add_to_db(guild_id, member_id) : adds a member to the database of the respective server\n
    """

    def __init__(self, bot):
        self.bot = bot

        # Look up implementation inside the add_to_cache function docstring
        self._cache = {}
        asyncio.get_event_loop().create_task(self.load_cache())

        # Start the loop that dumps cache to database every 10 minutes
        self.update_level_db.start()

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
                        'username' : "deprecated",\n
                        'level' : "the level of the member",\n
                        'exp' : "the exp of the member", \n
                        'boost' : "the boost multiplier", \n
                        'ispaused' "whether or not the member is pasued":

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

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():

                # Set the table name
                table_name = "server_members" + str(guild_id)

                # The query to execute, $1 notation used for sanitization

                query = f"SELECT * FROM {table_name} WHERE id = $1"
                cur = await conn.cursor(query, member_id)

                # The data returned by querying the database, defaults to None if record was not present
                data = await cur.fetchrow()

            # Can only do this stuff if there actually is relevant data in the database, otherwise,
            # a separate function adds the default values into the database, this bit adds the data to the cache.
            if data:
                self._cache[guild_id][member_id] = {
                    'id': data.get('id'),
                    'username': data.get('username'),
                    'level': data.get('level'),
                    'exp': data.get('exp'),
                    'ispaused': data.get('ispaused'),
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
        async with self.bot.pool.acquire() as conn:
            table_name = "server_members" + str(guild_id)
            query = f"INSERT INTO {table_name} (id, username, level, exp, ispaused, boost) " \
                    f"VALUES ($1, $2, $3, $4, $5, $6)"
            await conn.execute(query, member_id, 'deprecated', 0, 0, False, 1)

    async def dump_single_guild(self, guildid: int):
        """
        Function that dumps all entries from a single guild in the cache to the database.

        :param guildid: the id of the guild whose cache entry needs to be dumped
        :return: None
        """
        data = self._cache[guildid]
        table_name = 'server_members' + str(guildid)
        for memberid in data:
            current = data[memberid]
            query = f"UPDATE {table_name} " \
                    f"SET level = $1, " \
                    f"exp = $2, " \
                    f"ispaused = $3, " \
                    f"boost = $4" \
                    f"WHERE id = $5"

            await self.bot.pool.execute(query,
                                        current['level'],
                                        current['exp'],
                                        current['ispaused'],
                                        current['boost'],
                                        memberid)

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

        table_name = 'server_members' + str(guild.id)

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                top10 = []
                rank = 1
                async for entry in conn.cursor(f"SELECT id, exp, level FROM {table_name} ORDER BY exp DESC LIMIT $1", limit):
                    top10 += [{'rank': rank, 'id': entry.get('id'), 'exp': entry.get('exp'), 'level': entry.get('level')}]
                    rank += 1
                return top10

    @tasks.loop(minutes=10)
    async def update_level_db(self):
        """
        Loop that dumps the cache into db every 10 minutes

        :return: None
        """
        for guildId in self._cache:
            await self.dump_single_guild(guildId)
            self._cache[guildId] = {}
        print("Database updated")

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

    @commands.command()
    async def level(self, ctx: commands.Context, target: discord.Member = None):
        """
        Displays the level and exp points of a target specified
        If no target specified, shows own level
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
        Shows the top 10 server members based off their exp
        """
        data = await self.fetch_top_n(ctx.guild, limit=10)

        embed = discord.Embed(title="Server leaderboard",
                              colour=discord.Colour.green())
        for entry in data:
            embed.add_field(name=f"{entry.get('rank')}.{ctx.guild.get_member(entry.get('id'))}",
                            value=f"Level: {entry.get('level')} Exp: {entry.get('exp')}",
                            inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def setmultiplier(self, ctx: commands.Context, target: discord.Member, multiplier: int):
        """
        Command to set the multiplier of a member, setting it to 0 will make it so they don't get any level, eliminating
        the need of having an "ispaused" field in the database which will be removed soon.\n
        :param ctx:
        :param target:
        :param multiplier:
        :return:
        """
        if target.id not in self._cache[ctx.guild.id]:
            await self.add_to_cache(ctx.guild.id, target.id)
            self._cache[ctx.guild.id][target.id]['boost'] = int(multiplier)
        await ctx.send(f"{target}'s multiplier has been set to {multiplier}")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def giveexp(self, ctx: commands.Context, target: discord.Member, amount: int):
        await self.give_exp(ctx.guild.id, target.id, amount=int(amount))
        e = discord.Embed(title="Success",
                          description=f"Added {amount} points to {target.mention}",
                          colour=discord.Colour.green())
        await ctx.send(embed=e)

    @commands.command()
    @commands.check(is_me)
    async def update_db(self, ctx):
        """
        Command to update the database manually, mostly used for testing purposes, or when planning to take bot down
        for maintenance 
        :param ctx:
        :return:
        """
        await self.update_level_db()
        await ctx.send("db updated (hopefully)")


def setup(bot: commands.Bot):
    bot.add_cog(LevelSystem(bot))
