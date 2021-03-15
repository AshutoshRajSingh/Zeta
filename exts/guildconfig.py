import discord
from discord.ext import commands


class GuildConfig(commands.Cog, name="Configuration"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def prefix(self, ctx: commands.Context, new_prefix: str) -> None:
        """
        Used to set server prefix
        new_prefix here is the new server prefix that will be used for commands, can be up to 10 characters long
        """
        if len(new_prefix) > 10:
            await ctx.send("Prefix must be less than 10 characters long")
            return
        else:
            self.bot.prefixes[ctx.guild.id] = new_prefix
            async with self.bot.pool.acquire() as conn:

                await conn.execute("INSERT INTO guilds (id, prefix) "
                                   "VALUES ($1, $2) ON CONFLICT (id) DO "
                                   "UPDATE SET prefix = $3 WHERE guilds.id = $4",
                                   ctx.guild.id,
                                   new_prefix,
                                   new_prefix,
                                   ctx.guild.id)

                e = discord.Embed(title='Success!',
                                  description=f"The prefix for this server has been set to `{new_prefix}`",
                                  colour=discord.Colour.green())
                await ctx.send(embed=e)


def setup(bot: commands.Bot):
    bot.add_cog(GuildConfig(bot))
