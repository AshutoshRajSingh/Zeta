import discord
from discord.ext import commands


# Will customize later.
class MyHelp(commands.MinimalHelpCommand):
    def __init__(self):
        super().__init__()


hc = MyHelp()


def setup(bot: commands.Bot):
    bot.help_command = hc
