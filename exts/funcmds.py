import discord
from discord.ext import commands
import datetime


class funcmds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def bday(self, ctx: commands.Context, target: discord.Member):
        """
        Fetches a member's birthday from the database, they need to have registered their birthday in that particular
        guild for it to work.

        :param ctx: invocation context
        :param target: Target whose birthday to fetch
        :return:
        """

        async with self.bot.conn.transaction():
            # Table name :kekw:
            table_name = "server_members" + str(ctx.guild.id)

            query = f"SELECT id, birthday FROM {table_name}" + " WHERE id = $1"

            cur = await self.bot.conn.cursor(query, target.id)
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


def setup(bot: commands.Bot):
    bot.add_cog(funcmds(bot))

