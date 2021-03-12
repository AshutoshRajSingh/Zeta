import os
import util
import discord
import asyncpg
import datetime
from discord.ext import commands


def start(bot: commands.Bot):
    async def connect_to_db():
        bot.pool = await asyncpg.create_pool(os.environ['DATABASE_URL'], max_size=20)
        print(f"Connection to database made at {datetime.datetime.utcnow()}")

    bot.loop.run_until_complete(connect_to_db())
    db = util.DB(bot.pool)
    bot.db = db

    async def check_tables():
        """
        coro to check if tables exist for all guilds the bot is in, on startup and create table for any guild that isn't
        there but should be,
        """
        await bot.wait_until_ready()
        for guild in bot.guilds:
            await db.create_member_table(guild=guild)
            await db.make_guild_entry(guild.id)

    async def change_presence():
        await bot.wait_until_ready()
        await bot.change_presence(activity=discord.Game("Ping me for usage"))

    async def load_prefixes():
        await bot.wait_until_ready()
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                async for entry in conn.cursor("SELECT id, prefix FROM guilds"):
                    bot.prefixes[entry.get('id')] = entry['prefix']

    bot.loop.create_task(load_prefixes())
    bot.loop.create_task(check_tables())
    bot.loop.create_task(change_presence())
