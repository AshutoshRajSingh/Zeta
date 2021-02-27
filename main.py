import os
import sys
import time
import discord
import asyncpg
import asyncio
import datetime

from discord.ext import commands

# Store time of starting
start = datetime.datetime.utcnow()

intents = discord.Intents.all()

"""-------------------Doing all the command prefix stuff here---------------------------"""


async def load_prefixes(bott: commands.Bot):
    await bott.wait_until_ready()
    async with bott.pool.acquire() as conn:
        async with conn.transaction():
            async for entry in conn.cursor("SELECT id, prefix FROM guilds"):
                bott.prefixes[entry.get('id')] = entry['prefix']


async def get_pre(bott: commands.Bot, message: discord.Message):
    prefix = bott.prefixes.get(message.guild.id)
    if prefix:
        return prefix
    else:
        return "."


bot = commands.Bot(command_prefix=get_pre, intents=intents)
bot.prefixes = {}
bot.remove_command('help')

"""---------------Database Utility Functions-----------------------"""


async def create_member_table(**kwargs):
    """Function to create a member table in the database for a particular guild, accepts both the guild as in a
    discord.Guild object or simply the id of a guild, both accepted as keyword arguments

    kwargs:

    guild : the discord.Guild object\n
    guild_id : the id of the guild
    """
    if 'guild' in kwargs:
        guild_id = kwargs['guild'].id
    elif 'guild_id' in kwargs:
        guild_id = kwargs['guild_id']
    else:
        raise ValueError("Guild id / guild not supplied.")

    if type(guild_id) is not int:
        raise ValueError("Guild id must be int")

    async with bot.pool.acquire() as con:
        await con.execute(f"CREATE TABLE IF NOT EXISTS server_members{guild_id} ("
                          f"id bigint, "
                          f"username varchar(255), "
                          f"level int, "
                          f"exp int, "
                          f"ispaused boolean, "
                          f"boost int, "
                          f"birthday date)")

        await con.execute("INSERT INTO guilds (id) "
                          "VALUES ($1) ON CONFLICT (id) DO NOTHING", guild_id)


"""-----------------------Important things that need to happen as bot starts-------------------"""


async def connect_to_db():
    bot.pool = await asyncpg.create_pool(os.environ['DATABASE_URL'], ssl='require', max_size=20)


async def check_tables():
    """
    coro to check if tables exist for all guilds the bot is in, on startup and create table for any guild that isn't
    there but should be,
    """
    await bot.wait_until_ready()
    for guild in bot.guilds:
        await create_member_table(guild=guild)


async def change_presence():
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Game("Type .help for usage!"))


asyncio.get_event_loop().run_until_complete(connect_to_db())
asyncio.get_event_loop().create_task(check_tables())
asyncio.get_event_loop().create_task(change_presence())
asyncio.get_event_loop().create_task(load_prefixes(bot))

"""------------Events that I didn't bother making a separate cog for, if they become too much might do the same------"""


@bot.event
async def on_guild_join(guild):
    await create_member_table(guild=guild)


"""----------------------------Commands-------------------------------------------------------------------"""


def get_privileged_intents():
    retval = ""
    if bot.intents.members:
        retval += "members\n"
    if bot.intents.presences:
        retval += "presences\n"
    return retval


@bot.command()
async def info(ctx: commands.Context):
    e = discord.Embed(title=f"{bot.user.name}",
                      description=f"A big dumdum discord bot made by {bot.get_user(501451372147769355)}",
                      colour=discord.Colour.blue())

    # Calculate uptime
    uptime = datetime.datetime.utcnow() - start
    hours = int(uptime.seconds / 3600)
    mins = (uptime.seconds // 60) % 60
    secs = uptime.seconds - (hours * 3600 + mins * 60)
    e.add_field(name="Uptime", value=f"{hours}:{mins}:{secs}", inline=True)
    e.add_field(name="Websocket latency", value=f"{int(bot.latency * 1000)}ms", inline=True)

    # Calculate database latency
    temp_start = time.time()
    await bot.pool.execute('select')
    e.add_field(name="Database latency", value=f"{int((time.time() - temp_start) * 1000)}ms", inline=True)

    e.add_field(name="Servers joined", value=len(bot.guilds), inline=True)
    e.add_field(name="Users watched", value=len(bot.users), inline=True)
    e.add_field(name="Privileged Intents", value=get_privileged_intents())
    e.add_field(name="Python version", value=f"{sys.version[:5]}")
    e.add_field(name="discord.py version", value=f"{discord.__version__}")
    e.add_field(name="asyncpg version", value=f"{asyncpg.__version__}")
    await ctx.send(embed=e)


"""-----------Load all the extensions one at a time like an absolute peasant heheheheheueueue-----------"""

bot.load_extension('exts.level_system')
bot.load_extension('exts.helpcmd')
bot.load_extension('exts.funcmds')
bot.load_extension('exts.GuildConfig')
bot.load_extension('exts.administration')
bot.load_extension('exts.errorhandler')
bot.load_extension('exts.utility')
bot.load_extension('jishaku')

print(f"Successfully started process at {datetime.datetime.utcnow()}")


bot.run(os.environ['BOT_TOKEN'])
