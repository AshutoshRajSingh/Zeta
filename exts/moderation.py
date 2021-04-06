import discord
import datetime
from main import Zeta
from typing import Union
from discord.utils import get
from discord.ext import commands, tasks


async def create_mute_role(guild: discord.Guild):
    """Creates a mute role in a guild, members having it can't send messages or add reactions"""
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

    def __init__(self, bot: Zeta):
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
        Prevents `@everyone` from sending messages/reactions
        Note that you need to have the server permission "manage messages" to use this command
        """
        await ctx.guild.default_role.edit(permissions=discord.Permissions(send_messages=False, add_reactions=False))
        await ctx.send(
            embed=discord.Embed(title="A server-wide lockdown is now in effect", colour=discord.Colour.red()))

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def unlock(self, ctx: commands.Context):
        """
        Reenables `@everyone` to send messages/reactions

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
        Mutes a member so they can't send messages/reactions"

        `target` here is the member you'd like to mute, time (optional) is the time you wish to mute them for, the only acceptable format for time is shown by the example:
        `1d 2h 4m`
        Setting the time to `1d 2h 4m` would mute your target for 1 day, 2 hours and 4 minutes
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
        Unmutes an already muted member

        target here is the member you wish to unmute, note that unmuting a member with a timed mute will end their mute period at that instant
        Note that you need to have the server permission "manage messages" to use this command
        """
        await self.perform_unmute(ctx.guild.id, target.id, datetime.datetime.utcnow())
        await ctx.send(embed=discord.Embed(description=f"Unmuted {target.mention}", colour=discord.Colour.green()))

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, target: discord.Member):
        """
        Kicks a member.
        `target` here is the member you would like to boot.
        Note that you need the server permission "kick members" to use this command.
        """
        await target.kick()
        await ctx.send(embed=discord.Embed(description=f"{target.mention} was kicked"))

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, target: discord.Member, *, reason: str = None):
        """
        Bans a member.
        `target` here is the member you would like to hammer.
        Note that you need the server permission "ban members" to use this command.
        """
        await target.ban(reason=reason)
        await ctx.send(embed=discord.Embed(description=f"{target.mention} was banned"))

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

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context, target: discord.Member, *, reason: str):
        """
        Use to warn a mischievous member.

        `target` here is the member you wish to warn, can be mention, id or username.
        `reason` here is the reason you wish to warn them for.

        This warning gets added to the member's infractions, use the `infractions` command to learn more.
        """
        await self.bot.pool.execute("INSERT INTO infractions (guildid, memberid, reason, time) VALUES ($1, $2, $3, $4)",
                                    ctx.guild.id, target.id, reason, datetime.datetime.utcnow())
        await ctx.send(embed=discord.Embed(description=f"{target.mention} was warned", colour=self.bot.Colour.red()))

    @commands.group(invoke_without_command=True, aliases=['infraction'])
    @commands.has_guild_permissions(manage_messages=True)
    async def infractions(self, ctx: commands.Context, target: discord.Member):
        """
        Used to see a member's infractions

        `target` here is the member whose infractions you wish to see, can be mention, id or username.
        """
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                embed = discord.Embed(title=f"Infractions for {target}", description="\n\n".join([f"(ID: **{record.get('id')}**), [{record.get('time').strftime('%d/%m/%Y') if record.get('time') else None}]\nReason: {record.get('reason')}" async for record in conn.cursor("SELECT id, reason, time FROM infractions WHERE memberid = $1 AND guildid = $2", target.id, ctx.guild.id)]), colour=discord.Colour.red())
                if not embed.description:
                    await ctx.send(f"{target} doesn't have any infractions")
                else:
                    await ctx.send(embed=embed)

    @infractions.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def delete(self, ctx: commands.Context, infraction_id: int):
        """
        Used to delete an infraction given its id.

        `infraction_id` here is the id of the **infraction** you wish to delete, the id of the infraction can be obtained by using the `infractions` command
        """
        rc = await self.bot.pool.execute("DELETE FROM infractions WHERE id = $1 AND guildid = $2", infraction_id, ctx.guild.id)
        if rc != 'DELETE 1':
            await ctx.send("Couldn't remove infraction, double check the id provided")
        else:
            await ctx.send("Infraction deleted successfully!")

    @infractions.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, target: discord.Member):
        """
        Used to clear all of a member's infractions.

        `target` here is the member whose infractions you wish to clear, can be mention, id or username. Note that this command will remove **all** infractions `target` has.
        """
        await self.bot.pool.execute("DELETE FROM infractions WHERE guildid = $1 AND memberid = $2", ctx.guild.id, target.id)
        await ctx.send(f"{target}'s infractions were cleared successfully")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        """
        Bulk deletes a set amount of messages

        `amount` is the number of messages you wish to delete (including the command itself)
        """
        await ctx.channel.purge(limit=amount+1)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purgebots(self, ctx: commands.Context, limit: int):
        """
        Bulk deletes messages sent by bots

        `limit` is the number of messages you wish to search through, setting it to 50 for example would mean bot searches through last 50 messages sent in the channel and deletes the ones created by bots.
        """
        await ctx.channel.purge(limit=limit, check=lambda m: m.author.bot)

    @commands.command(name='user-info', aliases=['userinfo'])
    @commands.has_guild_permissions(kick_members=True)
    async def userinfo(self, ctx: commands.Context, target: discord.Member):
        pass

    @commands.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def checkpermission(self, ctx: commands.Context, channel: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel], permission: str):
        """
        Displays channel overwrites for all roles/members that are explicitly set to either Allow or Deny, for a particular channel

        `channel` here is the channel you wish to see overwrites for, can be text channel, voice channel or category, preferably id for the last two types
        `permission` here is the overwrite you wish to view.

        For example, using the command:
        `checkpermision general manage_messages`
        would give a list of all the members/roles that have the permission `manage_messages` in the channel `general`
        """
        permission = permission.lower()
        guildperms = [str(p) for p, val in discord.Permissions.all_channel() if val is False]
        ignoredattrs = [
                           'PURE_FLAGS',
                           'VALID_NAMES',
                           'is_empty',
                           'pair',
                       ] + guildperms
        valid_perms = "  ".join([f'`{str(p)}`' for p in dir(discord.PermissionOverwrite) if
                                 not p.startswith('_') and str(p) not in ignoredattrs])

        if permission not in valid_perms or permission not in dir(discord.Permissions):
            return await ctx.send("Invalid permission entered, here's an alphabetical list of valid permission types: "+"\n"+valid_perms)

        e = discord.Embed(title=f"Members/Roles with {permission} permission in {channel}:",
                          description=" ".join([t.mention if getattr(ow, permission) is True else "" for t, ow in channel.overwrites.items()]),
                          colour=discord.Colour.dark_blue())
        if not e.description.strip():
            return await ctx.send(f"No roles/members have the overwrite {permission} explicitly set to **Allow** in {channel}")
        await ctx.send(embed=e)

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def viewallowedoverwrites(self, ctx: commands.Context, channel: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]):
        """
        Displays a list of all overwrites that have been explicitly set to Allow

        `channel` here is the channel you wish to see the explicitly allowed overwrites for, can be mention, id, or username.
        """
        e = discord.Embed(title=f"Explicitly allowed overwrites for {channel}:", description="", colour=discord.Colour.red())
        for k, v in channel.overwrites.items():
            temp = f"**{str(k)}**" + "\n"
            for p, val in v:
                if val is True:
                    temp += f"`{str(p)}` "
            if temp == f"**{str(k)}**" + "\n":
                temp = ""
            e.description += temp + "\n\n"

        await ctx.send(embed=e)

def setup(bot: Zeta):
    bot.add_cog(Moderation(bot))
