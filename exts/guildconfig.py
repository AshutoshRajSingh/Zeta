import json
import discord
from discord.ext import commands


class GuildConfig(commands.Cog, name="Configuration"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        """
        Loads guild preferences from database and yanks them into cache
        """
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                async for entry in conn.cursor('SELECT id, preferences FROM guilds'):
                    if entry.get('preferences') is None:
                        await self.create_default_guild_prefs(entry.get('id'))
                    else:
                        self.bot.guild_prefs[entry.get('id')] = json.loads(entry.get('preferences'))

    async def create_default_guild_prefs(self, guildid, **kwargs):
        """
        Method intended to create a default guild preferences dict for a guild.
        """
        default = {p: False for p in self.bot.plugins}
        if kwargs:
            for k, v in kwargs.items():
                if k in self.bot.plugins:
                    default[k] = v
        self.bot.guild_prefs[guildid] = default
        await self.bot.pool.execute('UPDATE guilds SET preferences = $1 WHERE id = $2', json.dumps(default), guildid)

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

    @commands.group(name='plugin', aliases=['plugins'], invoke_without_command=True)
    async def _plugin(self, ctx: commands.Context):
        """
        Base command for plugin related functionality.

        Doesn't do much by itself but has subcommands that can be used to enable/disable plugins.
        If used without a subcommand, sends a message detailing on what plugins are enabled/disabled for this server.
        """
        # hehe
        await ctx.send(embed=discord.Embed(title='Plugins for this server:',
                                           description='\n'.join([f"{k} : {'enabled' if v else 'disabled'}" for k, v in self.bot.guild_prefs[ctx.guild.id].items()]),
                                           colour=discord.Colour(0xFFB6C1)))

    @_plugin.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def enable(self, ctx: commands.Context, plugin: str):
        """
        Enables a plugin
        It enables everything in the plugin including the commands/auto alerts
        `plugin` here is the name of the plugin you would like to enable
        """
        if plugin.lower() in self.bot.plugins:
            # noinspection PyBroadException
            try:
                self.bot.guild_prefs[ctx.guild.id][plugin] = True
                await self.bot.pool.execute("UPDATE guilds SET preferences = $1 WHERE id = $2",
                                            json.dumps(self.bot.guild_prefs[ctx.guild.id]), ctx.guild.id)
                await ctx.send(embed=discord.Embed(title="Success!",
                                                   description=f"Plugin {plugin} enabled successfully!",
                                                   colour=discord.Colour.green()))
            except Exception:
                await ctx.send('An error occurred')

        else:
            await ctx.send(f"Invalid plugin name, use `{ctx.prefix}plugin` to get a list of valid plugin names")

    @_plugin.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def disable(self, ctx: commands.Context, plugin: str):
        """
         Disables a plugin, shutting down its entire functionality
         It disables everything from the plugin including the commands/auto alerts.
        `plugin` here is the name of the plugin you would like to enable
        """
        if plugin.lower() in self.bot.plugins:
            # noinspection PyBroadException
            try:
                self.bot.guild_prefs[ctx.guild.id][plugin] = False
                await self.bot.pool.execute("UPDATE guilds SET preferences = $1 WHERE id = $2",
                                            json.dumps(self.bot.guild_prefs[ctx.guild.id]), ctx.guild.id)
                await ctx.send(embed=discord.Embed(title="Success!",
                                                   description=f"Plugin {plugin} disabled successfully!",
                                                   colour=discord.Colour.red()))

            except Exception:
                await ctx.send('An error occurred')

        else:
            await ctx.send(f"Invalid plugin name, use `{ctx.prefix}plugin` to get a list of valid plugin names")


def setup(bot: commands.Bot):
    bot.add_cog(GuildConfig(bot))
