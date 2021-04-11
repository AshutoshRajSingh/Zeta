import asyncio
import discord
from main import Zeta
from discord.ext import commands
from discord.ext.commands import TextChannelConverter, RoleConverter


class ReactionRoles(commands.Cog, name="Reaction roles"):
    """
    Commands to create and edit "reaction roles" menus.
    """
    def __init__(self, bot: Zeta):
        self.bot = bot
        self._cache = {}

        # Used so frequently figured it'd be good to make them class attribs
        self.tcc = TextChannelConverter()
        self.rc = RoleConverter()

        # ree
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            self._cache[guild.id] = {}
            self._cache[guild.id] = await self.bot.db.fetch_guild_selfole_data(guild.id)

    async def check_payload(self, payload: discord.RawReactionActionEvent):
        """
        Checks the payload against internal cache, if a preconfigured reaction roles message and emoji are detected,
        returns the discord.Role object corresponding to it.
        Args:
            payload: discord.RawReactionActionEvent

        Returns:
            Optional[discord.Role]
        """
        guild = self.bot.get_guild(payload.guild_id)
        emoji = payload.emoji

        """
        Cache implementation:
        {
            guild_id: {
                message_id: {
                    emoji: roleid
                    }
                }
            }
        }    
        """

        if guild.id in self._cache:
            if payload.message_id in self._cache[guild.id]:
                if str(emoji) in self._cache[guild.id][payload.message_id]:
                    return guild.get_role(self._cache[guild.id][payload.message_id][str(emoji)])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Listener that takes care of assigning a role to a member based off their adding reaction
        Cog maintains an internal cache containing information about what reaction from what message from w
        hat guild corresponds to what role to be assigned
        """
        role: discord.Role = await self.check_payload(payload)
        if payload.user_id == self.bot.user.id:
            return
        if role:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Does the same thing as the one above it excepts removes a role from the user who unreacted from message
        """
        role: discord.Role = await self.check_payload(payload)

        if role:
            guild = self.bot.get_guild(payload.guild_id)
            member: discord.Member = guild.get_member(payload.user_id)
            await member.remove_roles(role)

    @commands.group()
    async def reacrole(self, ctx: commands.Context):
        """
        Base command for all the reaction role functionality, doesn't do anything by itself but has subcommands that aid in managing reaction roles
        """
        pass

    @reacrole.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def create(self, ctx: commands.Context, title: str, *roles: discord.Role):
        """
        Create a reaction roles menu

        `title` is the title of the role menu that will show up on the top. The first argument is always the title (Needs to be enclosed in double quotes if it has a space).

        `[roles...]` is a space-separated list of roles you wish to create the menu for, you can enter the id of the roles, their name (enclosed in double quotes if it has a space), or their mention.

        After you use this command it will guide you through creating the menu, including what reactions correspond to what role and which channel you want to put the role menu in.
        """
        brake = {}

        def check(_r, _u):
            return _u == ctx.author and _r.message == me and str(_r.emoji) not in brake

        me = await ctx.send(f'React with the reaction that will correspond to the role `{roles[0]}`')

        # Yes I know this is an ugly solution to avoid an unnecessary api request but it is ultimately the only solution
        # I could think of.
        try:
            r, u = await self.bot.wait_for('reaction_add', timeout=len(roles) * 20, check=check)
            brake[str(r.emoji)] = roles[0].id
        except asyncio.TimeoutError:
            await ctx.send("Timed out, please run the command again and this time be a little quicker to react.")
            return

        try:
            for role in roles[1:]:
                await me.edit(content=f'React with the reaction that will correspond to the role `{role}`')
                r, u = await self.bot.wait_for('reaction_add', timeout=len(roles) * 20, check=check)
                brake[str(r.emoji)] = role.id
        except asyncio.TimeoutError:
            await ctx.send('Timed out, please run the command again and this time be a little quicker to react.')
            return

        await ctx.send(
            'What channel do you wish to send this role menu in? Enter its id, name or mention it: #<channel>')

        for count in range(4):
            try:
                m = await self.bot.wait_for('message', check=lambda _m: _m.author == ctx.author and _m.channel == ctx.channel, timeout=30)
                chan = await self.tcc.convert(ctx, m.content)
                break
            except commands.BadArgument:
                if count == 3:
                    await ctx.send("Too many tries to enter channel, make sure I can actually see the channel you're "
                                   "referring to and use the entire command again")
                    return
                await ctx.send("Please enter the correct channel, if in doubt, try mentioning it, the `#channel` thing")
            except asyncio.TimeoutError:
                await ctx.send("Timed out")
                return

        e = discord.Embed(title=f"Role menu: {title}",
                          description="\n\n".join(f"{k} - {ctx.guild.get_role(v)}"for k, v in brake.items()),
                          colour=discord.Colour.blue())

        zero = await chan.send(embed=e)

        for k in brake:
            await zero.add_reaction(k)

        self._cache[ctx.guild.id][zero.id] = brake

        query = """
                INSERT INTO selfrole_lookup (guildid, channelid, messageid) 
                VALUES ($1, $2, $3)
                """
        await self.bot.pool.execute(query, ctx.guild.id, chan.id, zero.id)

        query = """
                INSERT INTO selfrole (messageid, emoji, roleid)
                VALUES ($1, $2, $3)
                """
        for k, v in brake.items():
            await self.bot.pool.execute(query, zero.id, k, v)

    @reacrole.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def edit(self, ctx: commands.Context, message_id: int):
        """
        Edits an already created reaction roles menu.

        `message_id` here is the id of the message of the role menu you wish to edit, after using this command it will guide you through the process of editing the menu, step by step.

        Note that you need the server permisson "manage roles" to use this command
        """

        # Standard wait_for check function for message inputs, makes sure the command user's messages in command channel are considered
        def message_check(m: discord.Message):
            return m.author == ctx.author and m.channel == ctx.channel

        # Standard reaction check that ensures no duplicate reacrole entry, just name the relevant message 'm' before adding this one to check kwarg in wait_for
        def reaction_check_nd(_r: discord.Reaction, _u):
            return _u == ctx.author and _r.message == m and str(_r.emoji) not in self._cache[ctx.guild.id][PM.id]

        if message_id in self._cache[ctx.guild.id]:

            # Not actually channel id int but I decided to name it that way anyway
            chanid = await self.bot.pool.fetchrow("SELECT channelid FROM selfrole_lookup WHERE messageid = $1", message_id)
            chan: discord.TextChannel = ctx.guild.get_channel(chanid['channelid'])

            # Currently need message content for title, might start saving title in db to avoid this api call idk
            try:
                PM: discord.Message = await chan.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("It would seem that the message for the role menu you're trying to edit has been deleted, please try creating a new one")
                return

            buttons = ["\U0001f1e6", "\U0001f1e7", "\U0001f1e8", "\U0001f1e9"]

            e1 = discord.Embed(title="What aspect of the menu do you wish to change?",
                               description="\U0001f1e6 - Add a role\n\n"
                                           "\U0001f1e7 - Remove existing role\n\n"
                                           "\U0001f1e8 - Edit the reaction of a role\n\n"
                                           "\U0001f1e9 - Change the title",
                               colour=discord.Colour.blue())
            # Send the initial menu
            menu = await ctx.send(embed=e1)

            for button in buttons:
                await menu.add_reaction(button)

            # We need the first reaction where the emoji is one of the buttons
            def button_check(_r, _u):
                return _u == ctx.author and _r.message == menu and str(_r.emoji) in buttons
            # Get the option the user chose
            try:
                r, u = await self.bot.wait_for('reaction_add', check=button_check, timeout=20)
            except asyncio.TimeoutError:
                await ctx.send("Timed out")
                return

            # If user wanted to add a new role to the menu
            if str(r.emoji) == buttons[0]:
                await menu.clear_reactions()
                await menu.edit(content="What role do you wish to be added? Enter its mention, id, or name", embed=None)

                # Get the role object for the new role to be added
                try:
                    m = await self.bot.wait_for('message', check=message_check, timeout=30)
                    newrole = await self.rc.convert(ctx, m.content)

                    if newrole.id in self._cache[ctx.guild.id][PM.id].values():
                        await ctx.send("Error: role already exists in the menu, perhaps you meant to edit it?")
                        return
                except asyncio.TimeoutError:
                    await ctx.send("Timed out")
                    return
                except commands.BadArgument:
                    await ctx.send("Role not found, please try again")
                    return

                m = await ctx.send(f"React on this message with the reaction that will correspond to the role `{newrole}`")

                # Get the reaction/emoji that will correspond to the new role and yank everything into db
                try:
                    r, u = await self.bot.wait_for('reaction_add', check=reaction_check_nd, timeout=30)
                    self._cache[ctx.guild.id][PM.id][str(r.emoji)] = newrole.id

                    query = """
                            INSERT INTO selfrole (messageid, emoji, roleid)
                            VALUES ($1, $2, $3)
                            """

                    await self.bot.pool.execute(query, PM.id, str(r.emoji), newrole.id)

                    # Standard way of getting the embed description of the role menu
                    newmenudesc = "\n\n".join([f"{k} - {ctx.guild.get_role(v)}" for k, v in self._cache[ctx.guild.id][PM.id].items()])

                    newembed = discord.Embed(title=PM.embeds[0].title,
                                             description=newmenudesc,
                                             colour=discord.Colour.blue())

                    await PM.edit(embed=newembed)
                    await PM.add_reaction(r.emoji)
                    await ctx.send("Menu edit completed successfully, you may now delete the messages other than the menu itself")

                except asyncio.TimeoutError:
                    await ctx.send("Timed out")

            elif str(r.emoji) == buttons[1]:
                # Gotta yank the buttons to make everything squeaky clean
                await menu.clear_reactions()
                await menu.edit(content="Enter the role you wish to remove from the menu, can be mention, id or name",
                                embed=None)

                try:
                    # Get role from user
                    m = await self.bot.wait_for('message', check=message_check, timeout=20)
                    role = await self.rc.convert(ctx, m.content)

                    # If user trying to edit reaction to role that wasn't even in the menu to begin with
                    if role.id not in self._cache[ctx.guild.id][PM.id].values():
                        raise commands.BadArgument("Role not in cache")

                    # Get the key to delete using the old fashioned way, and subsequently delete it
                    targetkey = ""
                    for key, value in self._cache[ctx.guild.id][PM.id].items():
                        if value == role.id:
                            targetkey = key
                            break
                    self._cache[ctx.guild.id][PM.id].pop(targetkey)

                    # After everything is done and dusted, make database entry and edit the menu
                    query = """
                            DELETE FROM selfrole WHERE messageid = $1 AND roleid = $2
                            """
                    await self.bot.pool.execute(query, PM.id, role.id)
                    newmenudesc = "\n\n".join(
                        [f"{k} - {ctx.guild.get_role(v)}" for k, v in self._cache[ctx.guild.id][PM.id].items()])

                    newembed = discord.Embed(title=PM.embeds[0].title,
                                             description=newmenudesc,
                                             colour=discord.Colour.blue())
                    await PM.edit(embed=newembed)
                    await PM.clear_reaction(targetkey)
                    await ctx.send(
                        "Menu edit completed successfully, you may now delete the messages other than the menu itself")
                except asyncio.TimeoutError:
                    await ctx.send("Timed out")
                    return
                except commands.BadArgument:
                    await ctx.send("I don't think that role exists in that menu, run the command again")
                    return

            elif str(r.emoji) == buttons[2]:
                # Same drill, remove buttons to make it look clean
                await menu.clear_reactions()
                await menu.edit(embed=None, content="Enter the role for which you wish to change the reaction.")

                try:
                    m = await self.bot.wait_for('message', check=message_check, timeout=20)
                    role = await self.rc.convert(ctx, m.content)

                    if role.id not in self._cache[ctx.guild.id][PM.id].values():
                        raise commands.BadArgument("Role not in cache")

                except asyncio.TimeoutError:
                    await ctx.send("Timed out")
                    return
                except commands.BadArgument:
                    await ctx.send("Couldn't find the role you wished to edit in the menu")
                    return

                # Get the reaction/emoji that will correspond to the new role and yank everything into db
                m = await ctx.send(f"React on this message with the new reaction that will correspond to the role {role}")
                try:
                    r, u = await self.bot.wait_for('reaction_add', check=reaction_check_nd, timeout=30)

                    # Can only delete entry if have the key so....
                    TargetKey = ""  # Set default value so IDE stops screaming
                    for k, v in self._cache[ctx.guild.id][PM.id].items():
                        if v == role.id:
                            TargetKey = k

                    # Make new entry and delete the old one
                    self._cache[ctx.guild.id][PM.id][str(r.emoji)] = role.id
                    self._cache[ctx.guild.id][PM.id].pop(TargetKey)

                    # After everything is done and dusted, at last update the database entry
                    await self.bot.pool.execute("UPDATE selfrole SET emoji = $1 WHERE roleid = $2 AND messageid = $3", str(r.emoji), role.id, PM.id)

                    # Hehehehehehe
                    newmenudesc = "\n\n".join(
                        [f"{k} - {ctx.guild.get_role(v)}" for k, v in self._cache[ctx.guild.id][PM.id].items()])

                    newembed = discord.Embed(title=PM.embeds[0].title,
                                             description=newmenudesc,
                                             colour=discord.Colour.blue())

                    await PM.edit(embed=newembed)
                    await PM.clear_reaction(TargetKey)
                    await PM.add_reaction(str(r.emoji))
                    await ctx.send(
                        "Menu edit completed successfully, you may now delete the messages other than the menu itself")
                except asyncio.TimeoutError:
                    await ctx.send("Timed out")
                    return

            elif str(r.emoji) == buttons[3]:
                # This one speaks for itself I think.
                await menu.clear_reactions()
                await menu.edit(embed=None, content="Enter the new title you want the menu to have")
                try:
                    m = await self.bot.wait_for('message', check=message_check, timeout=30)
                    e = discord.Embed(title=f"Role menu: {m.content}",
                                      description=PM.embeds[0].description,
                                      colour=PM.embeds[0].colour)
                    await PM.edit(embed=e)
                except asyncio.TimeoutError:
                    await ctx.send("Timed out")
                    return

        else:
            await ctx.send("Menu not found in this server, double check if the id was entered correctly")


def setup(bot: Zeta):
    bot.add_cog(ReactionRoles(bot))
