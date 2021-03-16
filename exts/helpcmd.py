import discord
from discord.ext import commands


class MyHelp(commands.MinimalHelpCommand):
    def __init__(self):
        super().__init__()

    @staticmethod
    def _get_command_signature(command):
        return f"`{command.qualified_name}`"

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Commands",
                              description=f"Use {self.clean_prefix}help [command] for more info on a command.\nYou can also use {self.clean_prefix}help [category] for more info on a category.",
                              colour=discord.Colour.purple())
        for cog, _commands in mapping.items():
            try:
                if cog.qualified_name == 'Jishaku':
                    continue
            except AttributeError:
                pass
            filtered = await self.filter_commands(_commands, sort=True)
            command_signatures = [self._get_command_signature(c) for c in filtered]
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "Other")
                embed.add_field(name=cog_name, value=", ".join(command_signatures))

        channel = self.get_destination()
        await channel.send(embed=embed)

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
        desc = "\n\n".join([f"{cmd.name} - {cmd.help.splitlines()[0]}" for cmd in cmds if cmd.hidden is False])
        e = discord.Embed(title=f"{cog.qualified_name}",
                          description=cog.description + "\n\n" + desc,
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
