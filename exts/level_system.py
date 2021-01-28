import discord
from discord.ext import commands, tasks
from math import floor, sqrt


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

        # Start the loop that dumps cache to database every 10 minutes
        self.update_level_db.start()

    async def give_exp(self, guild_id: int,  member_id: int, amount=None) -> None:
        """
        Function to give exp to a particular member

        Parameters:
        :param guild_id: The id of the guild in question
        :param member_id: The id of the member in the guild
        :param amount: The amount of exp to give, default to None in which case the default level up exp is awarded
        :return: None
        """
        if not amount:
            amount = 5*self._cache[guild_id][member_id]['boost']
        self._cache[guild_id][member_id]['exp'] += amount

    async def add_to_cache(self, guild_id: int, member_id: int):
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
        :return: None
        """

        # Create the table if by any chance it does not exist
        await self.bot.conn.execute(f"CREATE TABLE IF NOT EXISTS server_members{guild_id} ("
                                    f"id bigint, "
                                    f"username varchar(255), "
                                    f"level int, "
                                    f"exp int, "
                                    f"ispaused boolean, "
                                    f"boost int, "
                                    f"birthday date)")

        async with self.bot.conn.transaction():

            # Set the table name
            table_name = "server_members" + str(guild_id)

            # The query to execute, $1 notation used for sanitization
            query = f"SELECT * FROM {table_name} WHERE id = $1"
            cur = await self.bot.conn.cursor(query, member_id)

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

    async def add_to_db(self, guild_id: int,  member_id: int) -> None:
        """
        A function that adds a new entry to the database with default values

        (and not dump existing cache into database)

        :param guild_id: The relevant guild
        :param member_id: The id of the member
        :return: None
        """
        async with self.bot.conn.transaction():
            table_name = "server_members" + str(guild_id)
            query = f"INSERT INTO {table_name} (id, username, level, exp, ispaused, boost) " \
                    f"VALUES ($1, $2, $3, $4, $5, $6)"
            await self.bot.conn.execute(query, member_id, 'deprecated', 0, 0, False, 1)

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

            await self.bot.conn.execute(query,
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

        async with self.bot.conn.transaction():
            top10 = ""
            rank = 1
            cur = self.bot.conn.cursor(f"SELECT id, exp FROM {table_name} ORDER BY exp DESC LIMIT $1", limit)
            async for entry in cur:
                top10 += f"{rank}. {guild.get_member(entry.get('id'))}, exp: {entry.get('exp')}\n"
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
        self._cache = {}
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
                                      description=f"GZ on level {NewLevel}, {message.author.mention}")
                await message.channel.send(embed=embed)

    @commands.command()
    async def level(self, ctx, target: discord.Member = None):
        """
        Displays the level and exp points of a target specified
        If no target specified, shows own level
        """
        if not target:
            target = ctx.author
        if ctx.guild.id in self._cache and target.id in self._cache[ctx.guild.id]:
            data = self._cache[ctx.guild.id][target.id]
            embed = discord.Embed(title=f"{target}",
                                  description=f"You are currently on level : {data['level']}\n"
                                              f"With exp : {data['exp']}",
                                  colour=discord.Colour.blue())
            await ctx.send(embed=embed)
        else:
            await self.add_to_cache(ctx.guild.id, target.id)
            await self.level(ctx, target)

    @commands.command()
    async def lb(self, ctx):
        """
        Shows the top 10 server members based off their exp
        """
        data = await self.fetch_top_n(ctx.guild, limit=10)
        embed = discord.Embed(title="Server leaderboard",
                              description=data,
                              colour=discord.Colour.green())
        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(is_me)
    async def setmultiplier(self, ctx: commands.Context, target: discord.Member, multiplier: int):
        if target.id not in self._cache[ctx.guild.id]:
            await self.add_to_cache(ctx.guild.id, target.id)
            self._cache[ctx.guild.id][target.id]['boost'] = int(multiplier)
        await ctx.send(f"{target}'s multiplier has been set to {multiplier}")

    @commands.command()
    @commands.check(is_me)
    async def update_db(self, ctx):
        await self.update_level_db()
        await ctx.send("db updated (hopefully)")


def setup(bot: commands.Bot):
    bot.add_cog(LevelSystem(bot))
