import os
import sys
import util
import asyncpg
import discord
import datetime
import traceback
from discord.ext import commands


class Zeta(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix=self.get_pre, **kwargs)
        print(f"All dates/time are in UTC unless stated otherwise\n"
              f"Started process at {datetime.datetime.utcnow()}")
        util.startup.start(self)
        self.prefixes = {}
        self.guild_prefs = {}
        self.Color = util.Color
        self.Colour = self.Color
        self.plugins = ['levelling', 'birthdays']
        self.initinit = False
        self.token = kwargs.get('token')
        self.load_exts()

    async def get_pre(self, _bot: commands.Bot, message: discord.Message):
        if message.guild is None:
            return '.'
        prefix = self.prefixes.get(message.guild.id)
        if prefix:
            return prefix
        else:
            return "."

    def load_exts(self):
        extensions = [
            'guildconfig',
            'genevents',
            'commanderrorhandler',
            'levelsystem',
            'moderation',
            'birthdaysystem',
            'reactionroles',
            'utility',
            'fun',
            'misc',
            'helpcmd',
            '_jishaku',
        ]
        print("Loading extensions...")
        for ext in extensions:
            if ext.startswith('_'):
                ext = ext[1:len(ext)]
            else:
                ext = 'exts.' + ext
            try:
                self.load_extension(ext)
                print(f"{ext} OK")
            except commands.ExtensionFailed as error:
                print(f"{ext} FAIL")
                traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def kickstart(self):
        self.run(self.token)


bot = Zeta(token=os.environ['BOT_TOKEN'])
bot.kickstart()
