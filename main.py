import discord
import asyncpg
import asyncio
import os
from discord.ext import commands

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
    bot.pool = await asyncpg.create_pool(os.environ['DATABASE_URL'], ssl='require')


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


asyncio.get_event_loop().create_task(connect_to_db())
asyncio.get_event_loop().create_task(check_tables())
asyncio.get_event_loop().create_task(change_presence())
asyncio.get_event_loop().create_task(load_prefixes(bot))


"""------------Events that I didn't bother making a separate cog for, if they become too much might do the same------"""


@bot.event
async def on_ready():
    print("successfully started process")


@bot.event
async def on_guild_join(guild):
    await create_member_table(guild=guild)


"""-----------Load all the extensions one at a time like an absolute peasant heheheheheueueue-----------"""


bot.load_extension('exts.level_system')
bot.load_extension('exts.helpcmd')
bot.load_extension('exts.funcmds')
bot.load_extension('exts.GuildConfig')
bot.load_extension('exts.administration')
bot.load_extension('jishaku')

# bot come alive
bot.run(os.environ['BOT_TOKEN'])
