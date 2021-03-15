import os
import sys
import util
import discord
import datetime
import traceback
from discord.ext import commands

print(f"All dates/time are in UTC unless stated otherwise\n"
      f"Started process at {datetime.datetime.utcnow()}")

intents = discord.Intents.all()


async def get_pre(_bot: commands.Bot, message: discord.Message):
    if message.guild is None:
        return '.'
    prefix = _bot.prefixes.get(message.guild.id)
    if prefix:
        return prefix
    else:
        return "."


bot = commands.Bot(command_prefix=get_pre, intents=intents, help_command=None)
bot.prefixes = {}
bot.initinit = False

# This takes care of doing the stuff that needs to happen as bot starts, for example establishing a connection
# to the database etc.
util.startup.start(bot)

"""---Call this inefficient but I like being able to exclude any extension by simply commenting out that line ree---"""

# Extensions inside exts dir named as is, extensions that are a site-package prefixed with '_' here currently jishaku
extensions = [
    'moderation',
    'fun',
    'commanderrorhandler',
    'birthdaysystem',
    'guildconfig',
    'helpcmd',
    'levelsystem',
    'utility',
    'genevents',
    'misc',
    'reactionroles',
    '_jishaku',
]

print("Loading extensions...")
for ext in extensions:
    if ext.startswith('_'):
        ext = ext[1:len(ext)]
    else:
        ext = 'exts.' + ext
    try:
        bot.load_extension(ext)
        print(f"{ext} OK")
    except commands.ExtensionFailed as error:
        print(f"{ext} FAIL")
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

bot.run(os.environ['BOT_TOKEN'])
