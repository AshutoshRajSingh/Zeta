import discord
from discord.ext import commands


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: commands.Context, *, tagname):
        query = "SELECT content FROM tags WHERE name = $1 AND guildid = $2"
        data = await self.bot.pool.fetchrow(query, tagname, ctx.guild.id)
        if data:
            content = data.get('content')
            await ctx.send(content)
        else:
            await ctx.send("Could not find the tag you're looking for, it may not have been created in this guild"
                           "scope")

    @tag.command()
    async def create(self, ctx: commands.Context, tagname, *, content):
        checkquery = "SELECT exists(SELECT content FROM tags WHERE name = $1 AND guildid = $2)"
        data = await self.bot.pool.fetchrow(checkquery, tagname, ctx.guild.id)
        if data.get('exists'):
            await ctx.send("A tag with that name already exists in this guild")
        else:
            insertquery = "INSERT INTO tags(name, content, guildid, authorid) VALUES ($1, $2, $3, $4)"
            await self.bot.pool.execute(insertquery, tagname, content, ctx.guild.id, ctx.author.id)
            await ctx.send(embed=discord.Embed(description=f"Tag {tagname} successfully created", colour=discord.Colour.green()))

    @tag.command()
    async def edit(self, ctx: commands.Context, tagname, *, content):
        query = "UPDATE tags SET content = $1 WHERE name = $2 AND guildid = $3 AND authorid = $4"
        retc = await self.bot.pool.execute(query, content, tagname, ctx.guild.id, ctx.author.id)

        if int(retc[7:]) == 1:
            await ctx.send(f"Tag {tagname} successfully updated")
        else:
            await ctx.send(f"Could not update tag {tagname} it may not exist or you may not be its owner")

    @tag.command()
    async def delete(self, ctx: commands.Context, tagname):
        if ctx.author.guild_permissions.manage_messages:
            query = "DELETE FROM tags WHERE name = $1 AND guildid = $2"
            await self.bot.pool.execute(query, tagname, ctx.guild.id)
            await ctx.send(f"Tag {tagname} successfully deleted")
        else:
            checkquery = "SELECT authorid FROM tags WHERE name = $1 AND guildid = $2"
            data = await self.bot.pool.fetchrow(checkquery, tagname, ctx.guild.id)
            if data.get('authorid'):
                if data.get('authorid') == ctx.author.id:
                    query = "DELETE FROM tags WHERE name = $1 AND guildid = $2"
                    await self.bot.pool.execute(query, tagname, ctx.guild.id)
                    await ctx.send(f"Tag `{tagname}` successfully deleted")
                else:
                    await ctx.send("You need to have the `manage_messages` permission to delete someone else's tags")
            else:
                await ctx.send("Tag not found")


def setup(bot: commands.Bot):
    bot.add_cog(UtilityCog(bot))
