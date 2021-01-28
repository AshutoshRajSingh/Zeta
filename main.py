import discord
import asyncpg
import asyncio
import os
from discord.ext import commands


intents = discord.Intents.all()

bot = commands.Bot(command_prefix=".", intents=intents)


async def connect_to_db():
    DATABASE_URL = os.environ['DATABASE_URL']
    await bot.wait_until_ready()
    bot.conn = await asyncpg.connect(DATABASE_URL, ssl='require')

asyncio.get_event_loop().create_task(connect_to_db())


@bot.event
async def on_ready():
    print("successfully started process")

bot.load_extension('exts.level_system')
bot.run(os.environ['BOT_TOKEN'])
