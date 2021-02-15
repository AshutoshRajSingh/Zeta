import discord
from discord.ext import commands, tasks
import asyncio
import datetime


class funcmds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bday_poll.start()

    @commands.command()
    async def bday(self, ctx: commands.Context, target: discord.Member):
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

    @staticmethod
    async def send_wish(guildid: int, memberid: int, when: datetime.datetime):
        title = f"{2} has their birthday today",
        description = "Reblog if u eating beans",
        colour = discord.Colour.blue()

    @tasks.loop(minutes=20)
    async def bday_poll(self):

        for guild in self.bot.guilds:
            if type(guild.id) is not int:
                raise ValueError("Somehow guild id is not an int")

            table_name = f"server_members{guild.id}"

            query = f"SELECT id, birthday FROM {table_name} " + "WHERE DATE_PART('day', birthday) = date_part('day', CURRENT_DATE) AND DATE_PART('month', birthday) = date_part('month', CURRENT_DATE)"
            async with self.bot.pool.acquire() as conn:
                async with conn.transaction():

                    # Temporary cursor to fetch the id of the channel to set alerts in
                    tempcur = await conn.cursor("SELECT id, bdayalert FROM guilds WHERE id = $1", guild.id)
                    tempdata = await tempcur.fetchrow()
                    try:
                        alert_channel_id = tempdata.get('bdayalert')
                        alert_time = tempdata.get('bdayalerttime')
                    except AttributeError:
                        pass

                    now = datetime.datetime.utcnow()
                    future = now + datetime.timedelta(minutes=20)

                    if alert_time:
                        if (future-alert_time).minutes < 20:
                            if alert_channel_id:
                                async for record in conn.cursor(query):
                                    self.bot.loop.create_task(self.send_wish(guild.id, record.get('id'), alert_time))

    @bday_poll.before_loop
    async def kellog(self):
        await self.bot.wait_until_ready()

    @commands.command()
    @commands.check(lambda ctx: ctx.author.id == 501451372147769355)
    async def checkbd(self, ctx):
        await self.bday_poll()


def setup(bot: commands.Bot):
    bot.add_cog(funcmds(bot))
