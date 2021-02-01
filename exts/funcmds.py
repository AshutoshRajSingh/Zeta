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
                table_name = "server_members" + str(ctx.guild.id)

                query = f"SELECT id, birthday FROM {table_name}" + " WHERE id = $1"

                cur = await conn.cursor(query, target.id)
                data = await cur.fetchrow()

            # If birthday existed in db
            if data.get('birthday'):
                birthday = data.get('birthday').strftime("%d %m %y")
            else:
                # Send error message if birthday wasn't found
                await ctx.send(f"Couldn't find {target}'s birthday in this server, tell them to set it using "
                               f"`{ctx.prefix}setbd`")
                # Short circuit
                return

        # Send the birthday as a message
        await ctx.send(f"{target}'s birthday was recorded to be on {birthday}")

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
        await self.bot.conn.execute(query, birthday, ctx.author.id)

        # Send confirmation message stating that the birthday was recorded successfully
        embed = discord.Embed(title="Birthday recorded!",
                              description=f"Your day is on {birthday}",
                              colour=discord.Colour.green())
        await ctx.send(embed=embed)

    @tasks.loop(hours=24)
    async def bday_poll(self):
        """Loop that runs once per day checking if a birthday has happened and sending relevant message in the guild"""

        for guild in self.bot.guilds:
            if type(guild.id) is not int:
                raise ValueError("Somehow guild id is not an int")

            table_name = f"server_members{guild.id}"

            query = f"SELECT id, birthday FROM {table_name} " + "WHERE DATE_PART('day', birthday) = date_part('day', CURRENT_DATE) AND DATE_PART('month', birthday) = date_part('month', CURRENT_DATE)"
            async with self.bot.pool.acquire() as conn:
                async with conn.transaction():
                    async for record in conn.cursor(query):
                        embed = discord.Embed(title=f"{self.bot.get_user(record.get('id'))} has their birthday today",
                                              description="Reblog if u eating beans",
                                              colour=discord.Colour.blue())
                        await (self.bot.get_channel(768403507878821888)).send(embed=embed)

    @bday_poll.before_loop
    async def kellog(self):
        await self.bot.wait_until_ready()

    @commands.command()
    @commands.check(lambda ctx: ctx.author.id == 501451372147769355)
    async def checkbd(self, ctx):
        await self.bday_poll()


def setup(bot: commands.Bot):
    bot.add_cog(funcmds(bot))
