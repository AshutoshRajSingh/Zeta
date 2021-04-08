import discord
from discord.ext import commands, menus

class bothelp(menus.Menu):
    """
    I wrote this shit and have absolutely no idea why it works but since it does I've decided to not touch it
    """
    def __init__(self, mapping: dict):
        self.mapping = mapping
        self.coglist = []
        self.current_page = 1
        self.listinate()
        super().__init__()

    def get_next_page(self):
        return self.coglist[3*self.current_page: 3*(self.current_page+1)]

    def listinate(self):
        for cog, cmds in self.mapping.items():
            try:
                if len(cog.get_commands()) == 0:
                    continue
                if cog.qualified_name.lower() == 'jishaku':
                    pass
            except AttributeError:
                self.coglist.append({"Other": cmds})
                continue
            self.coglist.append({cog.qualified_name: cmds})

    async def send_initial_message(self, ctx, channel):
        current = self.coglist[0:3]
        e = discord.Embed(title="cmds", colour=discord.Colour.purple())
        for item in current:
            for cog, cmds in item.items():
                if type(cog) is str:
                    e.add_field(name=cog, value=" ".join([f"`{cmd.name}`" for cmd in cmds]))
                else:
                    e.add_field(name=cog.qualified_name, value=" ".join([f"`{cmd.name}`" for cmd in cmds]))
        return await channel.send(embed=e)

    @menus.button("\U000025c0")
    async def backward(self, payload):
        self.current_page -= 2
        if self.current_page < 0:
            self.current_page = 1
            return
        await self.forward(payload)

    @menus.button("\U000023f9")
    async def stopme(self, payload):
        await self.message.delete()
        await self.stop()

    @menus.button("\U000025b6")
    async def forward(self, payload):
        current = self.get_next_page()
        if not current:
            return
        e = discord.Embed(title="cmds", colour=discord.Colour.purple())
        for item in current:
            for cog, cmds in item.items():
                if type(cog) is str:
                    e.add_field(name=cog, value=" ".join([f"`{cmd.name}`" for cmd in cmds]))
                else:
                    e.add_field(name=cog.qualified_name, value=" ".join([f"`{cmd.name}`" for cmd in cmds]))
        await self.message.edit(embed=e)
        self.current_page += 1

class MyHelp(commands.MinimalHelpCommand):
    def __init__(self):
        super().__init__()
        self.verify_checks = False

    @staticmethod
    def _get_command_signature(command):
        return f"`{command.qualified_name}`"

    async def send_bot_help(self, mapping):
        m = bothelp(mapping)
        await m.start(self.context)
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
