import discord
import asyncpg
import asyncio
import os
from discord.ext import commands


intents = discord.Intents.all()

bot = commands.Bot(command_prefix=".", intents=intents)
bot.remove_command('help')


async def connect_to_db():
    DATABASE_URL = os.environ['DATABASE_URL']
    await bot.wait_until_ready()
    bot.conn = await asyncpg.connect(DATABASE_URL, ssl='require')


async def change_presence():
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Game("Type .help for usage!"))


asyncio.get_event_loop().create_task(connect_to_db())
asyncio.get_event_loop().create_task(change_presence())


@bot.event
async def on_ready():
    print("successfully started process")

bot.load_extension('exts.level_system')
bot.load_extension('exts.helpcmd')
bot.load_extension('exts.funcmds')
bot.run(os.environ['BOT_TOKEN'])
