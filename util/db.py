class DB:
    """
    Class that contains predefined functions for commonly used database queries like the ones for fetching an entire
    row, deleting tables, rows etc.
    """
    def __init__(self, pool):
        self.pool = pool
        self.remove_guild = self.hakai_guild

    async def create_member_table(self, **kwargs):
        """
        Function to create a member table in the database for a particular guild, accepts both the guild as in a
        discord.Guild object or simply the id of a guild, both accepted as keyword arguments, if table already exists,
        it is ignored silently and nothing is changed. ie the table isn't created.

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
            raise TypeError("Guild id must be int")

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
        """
        Creates an entry for a guild in the guilds table, if already exists, gets ignored silently\n
        Args:
            guild_id: the id of table for which you wish to make the row

        Returns:

        """
        await self.pool.execute("INSERT INTO guilds (id) "
                                "VALUES ($1) ON CONFLICT (id) DO NOTHING", guild_id)

    async def remove_guild_entry(self, guild_id):
        """
        Yanks out a row from guilds table based on the id provided
        Args:
            guild_id: the id of the guild whose row you wish to delete

        Returns:
            None
        """
        await self.pool.execute("DELETE FROM guilds WHERE id = $1", guild_id)

    async def remove_guild_table(self, guild_id: int):
        """
        Yeets a guild table
        Args:
            guild_id: id of the guild to delete the table of

        Returns:
            None

        """
        if type(guild_id) is not int:
            raise TypeError("'guild_id' must be int")
        await self.pool.execute(f"DROP TABLE server_members{guild_id}")

    async def hakai_guild(self, guildid: int):
        await self.remove_guild_table(guildid)
        await self.remove_guild_entry(guildid)

    async def fetch_member(self, guildid, memberid):
        """
        Fetches a member from database
        Args:
            memberid: the id of the member to fetch
            guildid:  the id of the guild from whence to fetch the member

        Returns:
            dict like object containing db member information
        """
        if type(guildid) is not int:
            raise TypeError("'guildid' must be int")
        return await self.pool.fetchrow(f"SELECT * FROM server_members{guildid} WHERE id = $1", memberid)

    async def fetch_guild(self, guildid):
        """
        Fetches a guild from db and returns a dict like object containing the information
        Args:
            guildid: the id of the guild to fetch from db

        Returns:
            dict like object with db guild parameters
        """
        return await self.pool.fetchrow(f"SELECT * FROM guilds WHERE id = $1", guildid)

    async def make_member_entry(self, guildid, memberid):
        """
        Creates a member row in table with default values
        Args:
            memberid: id of the member
            guildid: id of the relevant guild

        Returns:
            None
        """

        async with self.pool.acquire() as conn:
            table_name = "server_members" + str(guildid)
            if type(guildid) is not int:
                raise TypeError('guildid must be int')

            query = f"INSERT INTO {table_name} (id, username, level, exp, ispaused, boost) " \
                    f"VALUES ($1, $2, $3, $4, $5, $6)"
            await conn.execute(query, memberid, 'deprecated', 0, 0, False, 1)

    async def fetch_guild_selfole_data(self, guildid):
        data = {}
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                async for entry in conn.cursor('SELECT * FROM selfrole WHERE guildid = $1', guildid):
                    if data.get(entry.get('messageid')) is None:
                        data[entry.get('messageid')] = {
                            entry.get('emoji'): entry.get('roleid')
                        }
                    else:
                        data[entry.get('messageid')][entry.get('emoji')] = entry.get('roleid')
        return data
