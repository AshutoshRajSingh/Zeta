import discord
from discord.ext import commands, menus

class bothelp(menus.Menu):
    def __init__(self, mapping: dict, prefix):
        self.clean_prefix = prefix
        self.embeddesc = f"Use {self.clean_prefix}help [command] for more info on a command.\nYou can also use {self.clean_prefix}help [category] for more info on a category."
        self.baseembed = discord.Embed(title="Commands", description=self.embeddesc, colour=discord.Colour.purple())
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
                    continue
            except AttributeError:
                self.coglist.append({"Other": cmds})
                continue
            self.coglist.append({cog.qualified_name: cmds})

    async def send_initial_message(self, ctx, channel):
        current = self.coglist[0:3]
        e = self.baseembed
        for item in current:
            for cog, cmds in item.items():
                if type(cog) is str:
                    e.add_field(name=cog, value=" ".join([f"`{cmd.name}`" for cmd in cmds]), inline=False)
                else:
                    e.add_field(name=cog.qualified_name, value=" ".join([f"`{cmd.name}`" for cmd in cmds]), inline=False)
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

        e = self.baseembed
        e.clear_fields()
        for item in current:
            for cog, cmds in item.items():
                if type(cog) is str:
                    e.add_field(name=cog, value=" ".join([f"`{cmd.name}`" for cmd in cmds]), inline=False)
                else:
                    e.add_field(name=cog.qualified_name, value=" ".join([f"`{cmd.name}`" for cmd in cmds]), inline=False)
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
        m = bothelp(mapping, self.clean_prefix)
        await m.start(self.context)

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
