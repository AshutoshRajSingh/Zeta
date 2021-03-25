import os
import sys
import util
import aiohttp
import asyncpg
import discord
import datetime
import traceback
from discord.ext import commands


class Zeta(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix=self.get_pre, intents=discord.Intents.all(), **kwargs)
        print(f"All dates/time are in UTC unless stated otherwise\n"
              f"Started process at {datetime.datetime.utcnow()}")
        self.pool: asyncpg.pool.Pool = None
        self.db: util.DB = None
        self.prefixes = {}
        self.guild_prefs = {}
        self.loop.run_until_complete(self.connect_to_db())
        self.loop.create_task(self.check_tables())
        self.loop.create_task(self._change_presence())
        self.loop.create_task(self.load_prefixes())
        self.Color = util.Color
        self.Colour = self.Color
        self.plugins = ['levelling', 'birthdays']
        self.initinit = False
        self.token = kwargs.get('token')
        self.load_exts()

    async def check_tables(self):
        """
        coro to check if tables exist for all guilds the bot is in, on startup and create table for any guild that isn't
        there but should be,
        """
        await self.wait_until_ready()
        for guild in self.guilds:
            await self.db.make_guild_entry(guild.id)

    async def _change_presence(self):
        """
        Changes the activity to a hardcoded value
        """
        await self.wait_until_ready()
        await self.change_presence(activity=discord.Game("Ping me for usage"))

    async def load_prefixes(self):
        """
        Loads server command prefixes from database then assigns them into a botvar bot.prefixes
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                async for entry in conn.cursor("SELECT id, prefix FROM guilds"):
                    self.prefixes[entry.get('id')] = entry['prefix']

    async def get_pre(self, _bot: commands.Bot, message: discord.Message):
        """
        Prefixes loaded on bot start and cached, if server hasn't set prefix, defaults to '.'
        """
        if message.guild is None:
            return '.'
        prefix = self.prefixes.get(message.guild.id)
        if prefix:
            return prefix
        else:
            return "."

    def load_exts(self):
        # Extensions that are inside exts dir put as is, exts that are a site package prefixed with _
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
