import discord
from discord.ext import commands


class MyHelp(commands.MinimalHelpCommand):
    def __init__(self):
        super().__init__()
        self.verify_checks = False

    @staticmethod
    def _get_command_signature(command):
        return f"`{command.qualified_name}`"

    async def send_bot_help(self, mapping):
        ignored_cogs = ['jishaku']
        addeddesc = f"""
        Use `{self.clean_prefix}list` to get a list of all the user commands.
        Use `{self.clean_prefix}help category` to list all commands in that category with a little info. 
        Use `{self.clean_prefix}help command` to get detailed information about using a command.     
        
        _Note that command and category names are case sensitive_       
        """
        e = discord.Embed(title="Help",
                          description=addeddesc,
                          colour=0xFFB6C1)
        for cog, cmds in mapping.items():

            if cog is not None:
                if len(cog.get_commands()) == 0 or cog.qualified_name.lower() in ignored_cogs:
                    continue
                name = cog.qualified_name
                if cog.description:
                    value = cog.description
                else:
                    value = "No desc found"
            else:
                name = None
                value = None

            if name is not None and value is not None:
                e.add_field(name=name, value=value, inline=False)
        chan = self.get_destination()
        await chan.send(embed=e)

    async def send_command_help(self, command):
        embed = discord.Embed(title="Command: " + command.qualified_name,
                              description=f"Usage:```{self.get_command_signature(command)}```\n" + command.help,
                              colour=discord.Colour.purple())
        alias = command.aliases
        if alias:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog):

        cmds = cog.get_commands()
        desc = "\n".join([f"`{cmd.name}` - {cmd.help.splitlines()[0]}" for cmd in cmds if cmd.hidden is False])
        e = discord.Embed(title=f"{cog.qualified_name}",
                          description=cog.description + "\n\n" + f"Use {self.clean_prefix}help [command] for more info on a command.\nYou can also use {self.clean_prefix}help [category] for more info on a category." + "\n\n" + "**Commands:**\n\n" + desc,
                          colour=discord.Colour.purple())
        chan = self.get_destination()
        await chan.send(embed=e)

    async def send_group_help(self, group):
        subcmds = "\n".join(
            [f"{self.clean_prefix}{group.qualified_name} {cmd.name} - {cmd.help.splitlines()[0]}" for cmd in
             group.commands])
        desc = f"Usage: ```{self.clean_prefix}{group.qualified_name} {group.signature}``` \n {group.help}\n\n Use {self.clean_prefix}help [command] for more info on a command.\nYou can also use {self.clean_prefix}help [category] for more info on a category.\n\n" + "**Commands:**"
        e = discord.Embed(title=f"Command: {group.qualified_name}",
                          description=desc + "\n" + subcmds,
                          colour=discord.Colour.purple())
        chan = self.get_destination()
        await chan.send(embed=e)


def setup(bot: commands.Bot):
    bot.help_command = MyHelp()
