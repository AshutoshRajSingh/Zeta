import io
import discord
import matplotlib
from discord.ext import commands
from matplotlib import pyplot as plt


def generate_plot(x, y):
    """
    Generates a plot based on given data and returns a python file like object that has the plot image encoded in png

    Args:
        x: iterable containing points in x axis
        y: iterable containing points in y axis

        (both have to be same length, duh)

    Returns: output_buffer : an io.BytesIO object that has the png image data.
    """
    fig, ax = plt.subplots(1, 1)
    ax.plot(x, y, color='white')
    fig.patch.set_facecolor('#2f3136')
    ax.set_facecolor('#2f3136')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    for child in ax.get_children():
        if isinstance(child, matplotlib.spines.Spine):
            child.set_color('white')
    temp = io.BytesIO()

    # Save plot into buffer
    fig.savefig(temp, format='png')
    temp.seek(0)

    return temp


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def delete_tag(self, tagname, guildid):
        query = "DELETE FROM tags WHERE name = $1 AND guildid = $2"
        await self.bot.pool.execute(query, tagname, guildid)

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: commands.Context, *, tagname):
        # Fetches a tag stored in db.
        query = "SELECT content FROM tags WHERE name = $1 AND guildid = $2"
        data = await self.bot.pool.fetchrow(query, tagname, ctx.guild.id)
        if data:
            content = data.get('content')
            await ctx.send(content)
        else:
            await ctx.send("Could not find the tag you're looking for, it may not have been created in this guild "
                           "scope")

    @tag.command()
    async def create(self, ctx: commands.Context, tagname, *, content):

        # Need to make sure that tag we're about to create doesn't already exist
        checkquery = "SELECT exists(SELECT content FROM tags WHERE name = $1 AND guildid = $2)"
        data = await self.bot.pool.fetchrow(checkquery, tagname, ctx.guild.id)
        if data.get('exists'):
            await ctx.send("A tag with that name already exists in this guild")
        else:
            # Basic sql query to insert data into the table
            insertquery = "INSERT INTO tags(name, content, guildid, authorid) VALUES ($1, $2, $3, $4)"
            await self.bot.pool.execute(insertquery, tagname, content, ctx.guild.id, ctx.author.id)
            await ctx.send(embed=discord.Embed(description=f"Tag {tagname} successfully created",
                                               colour=discord.Colour.green()))

    @tag.command()
    async def edit(self, ctx: commands.Context, tagname, *, content):
        query = "UPDATE tags SET content = $1 WHERE name = $2 AND guildid = $3 AND authorid = $4"

        # execute() returns postgres return code, we expect it to be "UPDATE 1" if tag edit was done successfully
        # otherwise it means that it wasn't
        retc = await self.bot.pool.execute(query, content, tagname, ctx.guild.id, ctx.author.id)

        # Send messages
        if int(retc[7:]) == 1:
            await ctx.send(f"Tag {tagname} successfully updated")
        else:
            await ctx.send(f"Could not update tag {tagname} it may not exist or you may not be its owner")

    @tag.command()
    async def delete(self, ctx: commands.Context, tagname):

        # If user has manage_messages permission, delete straignt away

        if ctx.author.guild_permissions.manage_messages:
            await self.delete_tag(tagname, ctx.guild.id)
            await ctx.send(f"Tag {tagname} successfully deleted")

        # Need to check if command user is the author of that tag or not
        else:
            checkquery = "SELECT authorid FROM tags WHERE name = $1 AND guildid = $2"
            data = await self.bot.pool.fetchrow(checkquery, tagname, ctx.guild.id)

            # Check if tag exists in the first place
            if data:
                # Check if user is tag author
                if data.get('authorid') == ctx.author.id:
                    await self.delete_tag(tagname, ctx.guild.id)
                    await ctx.send(f"Tag `{tagname}` successfully deleted")
                else:
                    await ctx.send("You need to have the `manage_messages` permission to delete someone else's tags")
            else:
                await ctx.send("Tag not found")

    @commands.command()
    async def plotdata(self, ctx: commands.Context, *, data: str):
        d = data.split(';')
        x = [float(e) for e in d[0].split(',')]
        y = [float(e) for e in d[1].split(',')]
        try:
            f = await self.bot.loop.run_in_executor(None, generate_plot, x, y)
        except ValueError:
            await ctx.send('Invalid data entered, please check if all values are numeric and there is an equal number '
                           'of them on both sides of the semicolon.')
            return

        file = discord.File(f, filename='plot.png')
        e = discord.Embed(title='Plot successful!', colour=discord.Colour.green())
        e.set_image(url='attachment://plot.png')
        e.set_footer(text=f'Requested by {ctx.author.display_name} | Powered by matplotlib',
                     icon_url=ctx.author.avatar_url)

        await ctx.send(file=file, embed=e)


def setup(bot: commands.Bot):
    bot.add_cog(Utility(bot))
