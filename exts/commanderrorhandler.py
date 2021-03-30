import sys
import asyncio
import discord
import traceback
from main import Zeta
from discord.ext import commands


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot: Zeta):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        """This function handles errors occurring during invocation and sending apropriate error message if applicable"""

        # The title is same across all the messages
        title = f"Error in command `{ctx.command.name}`"

        # Default description set to None, works as a flag in the event that an uncaught error is raised, in which case
        # it will not have gained any value
        description = None

        # Following block(s) handle general specific errors like missing permissions etc. Any that isn't caught here
        # Is printed in console as a standard exception
        if isinstance(error, commands.BadArgument):
            title = f"Error in command {ctx.command.name}"
            description = f"Bad parameter supplied, please use `{ctx.prefix}help {ctx.command.name}` " \
                          f"to get information about how to use that command"

        elif isinstance(error, commands.MissingRequiredArgument):
            description = str(error)

        elif isinstance(error, commands.MissingPermissions):
            description = str(error)

        elif isinstance(error, discord.Forbidden):
            description = "I can't do that, I may not have permission to do so, please check if my roles and role " \
                          "permissions are in order"

        elif isinstance(error, commands.CheckFailure):
            # Wanna keep these to local error handlers
            return

        # If the error was among the ones caught, description will have a non None value therefore we can send
        # an apropriate error message
        if description:
            e = discord.Embed(title=title, description=description, colour=discord.Colour.red())
            e.set_footer(text=f'{ctx.author}')

            # Adds the exclamation mark emoji reaction to the user's message
            await ctx.message.add_reaction('\U00002757')

            # Send apropriate error message and add waste basket reaction to it
            msg = await ctx.send(embed=e)
            await msg.add_reaction('\U0001f5d1')

            def check(r: discord.Reaction, u):
                return u == ctx.author and r.emoji == '\U0001f5d1' and r.message.id == msg.id

            # wait_for used to check if the command issuer reacted with the waste basket icon in the specified time
            # and if they did, delete that error message.
            try:
                await self.bot.wait_for('reaction_add', check=check, timeout=25)
                await ctx.message.remove_reaction('\U00002757', ctx.guild.me)
                await msg.delete()

            except asyncio.TimeoutError:
                await msg.remove_reaction('\U0001f5d1', ctx.guild.me)

        # All unhandled exceptions printed normally
        else:
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def setup(bot: Zeta):
    bot.add_cog(CommandErrorHandler(bot))
