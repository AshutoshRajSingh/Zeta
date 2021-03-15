import discord
from discord.ext import commands, tasks
from discord.utils import get
import datetime


async def create_mute_role(guild: discord.Guild):
    """Creates a mute role in a guild members having it can't send messages or add reactions"""
    perms = discord.Permissions.none()
    newrole = await guild.create_role(name="Muted", permissions=perms)

    ow = discord.PermissionOverwrite(send_messages=False, add_reactions=False)

    for channel in guild.channels:
        await channel.set_permissions(newrole, overwrite=ow)

    return newrole


# The database for mutes will be queried every this minutes
QUERY_INTERVAL_MINUTES = 30


# Converts a string of the format 1d 2h 3m into the equivalent number of minutes
def parsetime(time: str):
    arr = time.lower().split(' ')
    minutes = 0
    for elem in arr:
        if elem.endswith('h'):
            minutes += int(elem[0:len(elem) - 1]) * 60
        elif elem.endswith('m'):
            minutes += int(elem[0:len(elem) - 1])
        elif elem.endswith('d'):
            minutes += int(elem[0:len(elem) - 1]) * 60 * 24
    return minutes


class Moderation(commands.Cog):
    """
    Commands to deal with pesky trolls and spammers, all of them at one place
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cache = {}
        self.mute_poll.start()

    async def load_cache(self):
        """Loads cache for moderative actions, not in use currently but future plans involve this as requirement"""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            self._cache[guild.id] = {}

    # ------------------------------------Moderative actions--------------------------------------------

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def lockdown(self, ctx: commands.Context):
        """
        Removes the permissions "send_messages" and "add_reactions" from `@everyone`
        Note that you need to have the server permission "manage messages" to use this command
        """
        await ctx.guild.default_role.edit(permissions=discord.Permissions(send_messages=False, add_reactions=False))
        await ctx.send(
            embed=discord.Embed(title="A server-wide lockdown is now in effect", colour=discord.Colour.red()))

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def unlock(self, ctx: commands.Context):
        """
        Enables the permissions "send_messages" and "add_reactions" on `@everyone`
        Basically reverses what the lockdown command does
        Note that you need to have the server permission "manage messages" to use this command
        """
        await ctx.guild.default_role.edit(permissions=discord.Permissions.general())
        await ctx.send(
            embed=discord.Embed(title="Lockdown lifted", colour=discord.Colour.green()))

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def mute(self, ctx, target: discord.Member, *, time: str = None):
        """
        Mutes a member preventing them from sending messages/adding reactions in the server"
        `target` here is the member you'd like to mute, time (optional) is the time you wish to mute them for, the only acceptable format for time is shown by the example: `1d 2h 4m` Therefore setting the time to `1d 2h 4m` would mute your target for 1 day, 2 hours and 4 minutes
        Note that you need to have the server permission "manage messages" to use this command
        """
        mr = get(ctx.guild.roles, name="Muted")
        if not mr:
            await ctx.send("Server doesn't seem to have mute configured yet, stand by please.")
            async with ctx.channel.typing():
                mr = await create_mute_role(ctx.guild)
                await ctx.send("Configured mute successfully")

        if not time:
            await target.add_roles(mr)
            e = discord.Embed(description=f"{target} has been muted", colour=discord.Colour.red())
            e1 = discord.Embed(description=f"You have been muted from the server {ctx.guild} indefinitely, you'll only"
                                           f"be able to send messages if a moderator unmutes you",
                               colour=discord.Colour.red())
            await ctx.send(embed=e)
            await target.send(embed=e1)

        if time:
            await target.add_roles(mr)

            duration = parsetime(time)
            muted_till = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)

            await self.bot.pool.execute("INSERT INTO mutes (id, guildid, mutedtill) VALUES ($1, $2, $3)",
                                        target.id, ctx.guild.id, muted_till)

            e = discord.Embed(description=f"{target} has been muted till {muted_till}", colour=discord.Colour.red())
            e1 = discord.Embed(description=f"You have been muted from the server {ctx.guild} for {muted_till} (UTC)",
                               colour=discord.Colour.red())
            await ctx.send(embed=e)
            await target.send(embed=e1)

            if duration < QUERY_INTERVAL_MINUTES:
                self.bot.loop.create_task(self.perform_unmute(ctx.guild.id, target.id, muted_till))

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def unmute(self, ctx: commands.Context, target: discord.Member):
        """
        Unmutes an already muted member, allowing them to send messages/add reactions
        target here is the member you wish to unmute, note that unmuting a member with a timed mute will end their mute period at that instant
        Note that you need to have the server permission "manage messages" to use this command
        """
        await self.perform_unmute(ctx.guild.id, target.id, datetime.datetime.utcnow())
        await ctx.send(embed=discord.Embed(description=f"Unmuted {target.mention}", colour=discord.Colour.green()))

    async def perform_unmute(self, guildid, targetid, when: datetime.datetime):
        """Unmutes a target in a guild at a specified time"""

        # Gotta get the guild and member objects to perform the unmute
        guild = self.bot.get_guild(guildid)
        target = guild.get_member(targetid)

        # Neat little feature to sleep till a specified timestamp in UTC
        await discord.utils.sleep_until(when)

        # This checks if the target left the server because angry on being muted
        if target:
            # Remove the muted role, currently using get, in the near future might just save the muted role ids into
            # the database
            role = get(guild.roles, name='Muted')

            # Checks if member was already unmuted manually in which case no need to send the message
            if role in target.roles:
                await target.remove_roles(role)

                # Send a message to the target informing them that they were unmuted
                e = discord.Embed(
                    description=f"Your mute period has been completed, you will now be able to send messages in "
                                f"{guild} again.", colour=discord.Colour.green())
                await target.send(embed=e)

        # Gotta delete the entry from the database now that the unmute has been done
        await self.bot.pool.execute("DELETE FROM mutes WHERE id = $1 AND guildid = $2",
                                    targetid, guildid)

    @tasks.loop(minutes=QUERY_INTERVAL_MINUTES)
    async def mute_poll(self):
        """Background loop that takes care of querying the databse and looking up entries where the time till
        a target has been muted for is before the time the next iteration of the loop will happen."""
        await self.bot.wait_until_ready()
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                future = datetime.datetime.utcnow() + datetime.timedelta(minutes=QUERY_INTERVAL_MINUTES)
                async for entry in conn.cursor("SELECT * FROM mutes WHERE mutedtill < $1",
                                               future):
                    # Creating an async task to perform unmutes, the future handling is done in the perform_unmute
                    # function itself
                    self.bot.loop.create_task(self.perform_unmute(entry.get('guildid'),
                                                                  entry.get('id'),
                                                                  entry.get('mutedtill')))


def setup(bot: commands.Bot):
    bot.add_cog(Moderation(bot))
