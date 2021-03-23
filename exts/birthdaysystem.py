import discord
import datetime
from main import Zeta
from discord.ext import commands, tasks


class BirthdaySystem(commands.Cog, name="Birthday system"):
    """
    Commands related to birthdays and the like, saving, retrieving, and automatic alerts.
    """
    def __init__(self, bot: Zeta):
        self.bot = bot
        self.bday_poll.start()

    async def cog_check(self, ctx: commands.Context):
        try:
            return self.bot.guild_prefs[ctx.guild.id]['birthdays']
        except KeyError:
            return False

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            if ctx.guild.id not in self.bot.guild_prefs:
                await self.bot.db.create_default_guild_prefs(ctx.guild.id)
            if not self.bot.guild_prefs[ctx.guild.id].get('birthdays'):
                await ctx.send("The `birthdays` plugin has been disabled on this server therefore related commands will not work\n"
                               "Hint: Server admins can enable it using the `plugin enable` command, use the help command to learn more.")

    @commands.command()
    async def bday(self, ctx: commands.Context, target: discord.Member) -> None:
        """
        Sends a member's birthday as a message

        `target` here is the member whose birthday you wish to see, not that they need to have their birthday saved in this server using the setbd command
        """
        query = "SELECT birthday FROM server_members WHERE memberid = $1 AND guildid = $2"
        data = await self.bot.pool.fetchrow(query, target.id, ctx.guild.id)

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
    async def setbd(self, ctx: commands.Context, *, date_of_birth: str):
        """
        Command to save your birthday in the bot

        If you choose to do this, everyone **in this server** will be able to see your birthday and will get notified when the day arrives.
        The only acceptable format for your date of birth is "DD MM YYYY"
        """

        # Try except block to check if the date entered was of correct format
        try:
            datecheck = datetime.datetime.strptime(date_of_birth, "%d %m %Y")
        except ValueError:
            # Error message sent when date format isn't the one bot is looking for
            await ctx.send("Invalid date format, please try again, using `DD MM YYYY`")
            # Short circuit
            return

        # Yeet it into dabatase
        query = f"UPDATE server_members SET birthday=to_date($1, 'DD MM YYYY') WHERE memberid =  $2 AND guildid = $3"
        await self.bot.pool.execute(query, date_of_birth, ctx.author.id, ctx.guild.id)

        # Send confirmation message stating that the birthday was recorded successfully
        embed = discord.Embed(title="Birthday recorded!",
                              description=f"Your day is on {datecheck.strftime('%d %B %Y')}",
                              colour=discord.Colour.green())
        await ctx.send(embed=embed)

    async def send_wish(self, guildid: int, channelid: int, memberid: int, when: datetime.datetime):
        """
        Sends a birthday wish in a guild at a specified time in UTC
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
        # Future is the time of the next iteration of the loop
        now = datetime.datetime.utcnow()
        future = now + datetime.timedelta(minutes=20)

        # Query the database to find the time at which alert is to be sent out
        query1 = f"SELECT id, bdayalert, bdayalerttime FROM guilds WHERE bdayalerttime < $1 AND bdayalerttime > $2"

        # Query to fetch the members who have their birthday on that day
        query = "SELECT id, birthday FROM server_members WHERE DATE_PART('day', birthday) = DATE_PART('day', CURRENT_DATE) AND DATE_PART('month', birthday) = DATE_PART('month', CURRENT_DATE) AND guildid = $1"

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
                            try:
                                if self.bot.guild_prefs[guild_record['id']] is None:
                                    await self.bot.get_cog('Configuration').create_default_guild_prefs(guild_record['id'])
                                    continue
                                elif not self.bot.guild_prefs[guild_record['id']].get('birthdays'):
                                    continue
                            except KeyError:
                                await self.bot.get_cog('Configuration').create_default_guild_prefs(guild_record['id'])
                                continue

                            async for record in conn.cursor(query, guild_record.get('id')):
                                self.bot.loop.create_task(
                                    self.send_wish(guild_record['id'], alert_channel_id, record.get('memberid'), new_time))

    @bday_poll.before_loop
    async def kellog(self):
        await self.bot.wait_until_ready()

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def bdalerttime(self, ctx: commands.Context, *, time):
        """
        Sets the time of auto birthday alerts.

        The time provided must be in UTC and of the format "HH MM"
        Note that you need to have the "Manage server" permisission to use this command
        """
        tim = datetime.datetime.strptime(time, "%H %M").time()
        await self.bot.pool.execute("UPDATE guilds SET bdayalerttime = $1 WHERE id = $2", tim, ctx.guild.id)

        e = discord.Embed(title="Success!",
                          description=f"Birthday alerts will be sent out on this server at {tim.strftime('%H:%M')} (UTC)",
                          colour=discord.Colour.green())
        await ctx.send(embed=e)
        await self.bday_poll()

    @commands.command(hidden=True)
    @commands.check(lambda ctx: ctx.author.id == 501451372147769355)
    async def checkbd(self, ctx: commands.Context):
        await self.bday_poll()

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def bdchannel(self, ctx: commands.Context, alert_channel: discord.TextChannel):
        """
        Sets the channel for auto birthday alerts.

        Note that you need to have the server permission "Manage server"  to use this command
        """

        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE guilds SET bdayalert = $1 WHERE id = $2", alert_channel.id, ctx.guild.id)
            e = discord.Embed(title='Success!',
                              description=f'The channel {alert_channel.mention} will be used for auto birthday alerts',
                              colour=discord.Colour.green())
            await ctx.send(embed=e)


def setup(bot: Zeta):
    bot.add_cog(BirthdaySystem(bot))
