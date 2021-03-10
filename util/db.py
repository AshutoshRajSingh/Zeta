
class DB:
    def __init__(self, pool):
        self.pool = pool

    async def create_member_table(self, **kwargs):
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

        async with self.pool.acquire() as con:
            await con.execute(f"CREATE TABLE IF NOT EXISTS server_members{guild_id} ("
                              f"id bigint, "
                              f"username varchar(255), "
                              f"level int, "
                              f"exp int, "
                              f"ispaused boolean, "
                              f"boost int, "
                              f"birthday date)")

    async def make_guild_entry(self, guild_id):
        await self.pool.execute("INSERT INTO guilds (id) "
                                "VALUES ($1) ON CONFLICT (id) DO NOTHING", guild_id)
