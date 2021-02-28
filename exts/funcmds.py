import random
import aiohttp
import discord
import datetime
from discord.ext import commands, tasks


class funcmds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bday_poll.start()

    @commands.command()
    async def bday(self, ctx: commands.Context, target: discord.Member) -> None:
        """
        Fetches a member's birthday from the database, they need to have registered their birthday in that particular
        guild for it to work.

        :param ctx: invocation context
        :param target: Target whose birthday to fetch
        :return:
        """
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                # Table name :kekw:
                if type(ctx.guild.id) is not int:
                    raise ValueError("Guild id is somehow not int")

                table_name = "server_members" + str(ctx.guild.id)

                query = f"SELECT id, birthday FROM {table_name}" + " WHERE id = $1"

                cur = await conn.cursor(query, target.id)
                data = await cur.fetchrow()

            # If birthday existed in db
            if data.get('birthday'):
                birthday = data.get('birthday').strftime("%d %B")
            else:
                # Send error message if birthday wasn't found
                await ctx.send(f"Couldn't find {target}'s birthday in this server, tell them to set it using "
                               f"`{ctx.prefix}setbd`")
                # Short circuit
                return

        # Send the birthday as a message
        await ctx.send(f"{target}'s birthday is on {birthday}")

    @commands.command()
    async def setbd(self, ctx: commands.Context, *, birthday: str):
        """
        Saves the birthday of a member into that guild's table.
        Format: DD MM YYYY

        :param ctx: Invocation context
        :param birthday: (str) The birthday to save into the database
        :return: None
        """

        # Try except block to check if the date entered was of correct format
        try:
            datecheck = datetime.datetime.strptime(birthday, "%d %m %Y")
        except ValueError:
            # Error message sent when date format isn't the one bot is looking for
            await ctx.send("Invalid date format, please try again, using `DD MM YYYY`")
            # Short circuit
            return

        # Yeet it into dabatase
        table_name = f"server_members{ctx.guild.id}"
        query = f"UPDATE {table_name}" + " SET birthday=to_date($1, 'DD MM YYYY') WHERE id =  $2"
        await self.bot.pool.execute(query, birthday, ctx.author.id)

        # Send confirmation message stating that the birthday was recorded successfully
        embed = discord.Embed(title="Birthday recorded!",
                              description=f"Your day is on {datecheck.strftime('%d %B %Y')}",
                              colour=discord.Colour.green())
        await ctx.send(embed=embed)

    async def send_wish(self, guildid: int, channelid: int, memberid: int, when: datetime.datetime):
        """
        Sends a birthday wish in a guild at a specified time in UTC

        Args:
            guildid:
            channelid:
            memberid:
            when:

        Returns: None

        """
        await discord.utils.sleep_until(when)

        guild = self.bot.get_guild(guildid)
        channel = guild.get_channel(channelid)
        m = guild.get_member(memberid)
        e = discord.Embed(title=f"{m} has their birthday today!",
                          description=f"Reblog if u eating beans",
                          colour=discord.Colour.blue())

        await channel.send(embed=e)

    @tasks.loop(minutes=20)
    async def bday_poll(self):

        for guild in self.bot.guilds:

            if type(guild.id) is not int:
                raise TypeError("Somehow guild id is not an int")

            table_name = f"server_members{guild.id}"

            # Future is the time of the next iteration of the loop
            now = datetime.datetime.utcnow()
            future = now + datetime.timedelta(minutes=20)

            # Query the database to find the time at which alert is to be sent out
            query1 = f"SELECT id, bdayalert, bdayalerttime FROM guilds WHERE bdayalerttime < $1 AND bdayalerttime > $2"

            # Query to fetch the members who have their birthday on that day
            query = f"SELECT id, birthday FROM {table_name} " + "WHERE DATE_PART('day', birthday) = DATE_PART('day', CURRENT_DATE) AND DATE_PART('month', birthday) = DATE_PART('month', CURRENT_DATE)"

            async with self.bot.pool.acquire() as conn:
                async with conn.transaction():

                    async for guild_record in conn.cursor(query1, future, now):

                        # Converting alert time to string here as it needs to be merged with the whole
                        # date to make it datetime instead of just time
                        alert_time = guild_record.get('bdayalerttime').strftime("%H %M %S")
                        temp_time_str = datetime.datetime.utcnow().strftime('%d %m %y')

                        # Alert time is converted into datetime object with date of today
                        new_time = datetime.datetime.strptime(f"{temp_time_str} {alert_time}", "%d %m %y %H %M %S")

                        # Get the channel id in which to send alerts
                        alert_channel_id = guild_record.get('bdayalert')

                        # If an alert time and alert channel id have been set only then will an alert be sent.
                        if alert_time:
                            if alert_channel_id:
                                async for record in conn.cursor(query):
                                    self.bot.loop.create_task(
                                        self.send_wish(guild.id, alert_channel_id, record.get('id'), new_time))

    @bday_poll.before_loop
    async def kellog(self):
        await self.bot.wait_until_ready()

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def bdalerttime(self, ctx: commands.Context, *, time):
        """
        Sets the time of the day at which birthday alerts will be sent on a guild. (UTC)
        """
        tim = datetime.datetime.strptime(time, "%H %M").time()
        await self.bot.pool.execute("UPDATE guilds SET bdayalerttime = $1 WHERE id = $2", tim, ctx.guild.id)

        e = discord.Embed(title="Success!",
                          description=f"Birthday alerts will be sent out on this server at {tim.strftime('%H:%M')} (UTC)",
                          colour=discord.Colour.green())
        await ctx.send(embed=e)
        await self.bday_poll()

    @commands.command()
    @commands.check(lambda ctx: ctx.author.id == 501451372147769355)
    async def checkbd(self, ctx: commands.Context):
        await self.bday_poll()

    @commands.command(aliases=['r'])
    async def reddit(self, ctx: commands.Context, subreddit: str):
        ROUTE = 'https://www.reddit.com/r/%s.json'

        async with aiohttp.ClientSession() as cs:
            async with cs.get(ROUTE % subreddit) as r:
                d = await r.json()

        # Count the number of nsfw/video posts in the subreddit as they don't go to discord
        nsfw = 1
        video = 1

        # Max number of posts to look up
        MAX_LOOKUPS = 25

        # The reddit json api doesn't (seem to) return a 404 if subreddit doesn't exist, this seems like a workaround
        # To check if the sub doesn't exist/is private
        if len(d['data']['children']) == 0:
            await ctx.send("Subreddit not found! It may be private or might not exist.")
            return
        # There was an attempt to ignore video/nsfw posts however for the video part, if the sub is a video only sub
        # bad things happen and I really am not in the mood to investigate what's wrong (apparently the is_video bool
        # is incorrect for some posts)
        else:
            posts = d['data']['children']
            while nsfw < MAX_LOOKUPS and video < MAX_LOOKUPS:
                selected = random.choice(posts)
                if selected['data']['over_18']:
                    nsfw += 1
                    continue
                if selected['data']['is_video']:
                    video += 1
                    continue

                e = discord.Embed(title=selected['data']['title'],
                                  colour=discord.Colour.red())
                e.set_image(url=selected['data']['url_overridden_by_dest'])
                await ctx.send(embed=e)
                return

            if nsfw >= MAX_LOOKUPS:
                await ctx.send(f"Looked up {MAX_LOOKUPS} posts, all were nsfw, not posting")
            elif video >= MAX_LOOKUPS:
                await ctx.send(f"Looked up {MAX_LOOKUPS} posts, all were videos, can't post.")


def setup(bot: commands.Bot):
    bot.add_cog(funcmds(bot))
