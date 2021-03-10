import os
import sys
import asyncpg
import asyncio
import socket

"""
To have the database set up for you, 
get its url (format - postgres://<username>:<password>@<host>:<port>/<database_name>)

then use 
python autodb.py <database_url> init

(Without the <>)

ALTERNATIVELY 

If you have already set the os environment variable DATABASE_URL equal to the url of your database, use:

python autodb.py osenv init
"""


async def init(Url):

    try:
        conn = await asyncpg.connect(Url)
    except socket.gaierror:
        print("Couldn't connect to the database, possibly because invalid url provided, remember it has to be of the "
              "format - postgres://<username>:<password>@<host>:<port>/<database_name>")
        return

    queries = {
        'guilds': "CREATE TABLE guilds (id bigint PRIMARY KEY, prefix varchar(10), bdayalert bigint, bdayalerttime time)",
        'mutes': "CREATE TABLE mutes (id bigint, guildid bigint, mutedtill timestamp)",
        'tags': "CREATE TABLE tags (name varchar(100), authorid bigint, guildid bigint, content text)"
    }

    count = 0
    for key, value in queries.items():
        try:
            await conn.execute(value)
        except asyncpg.DuplicateTableError:
            print(f"{key} ALREADY EXISTS")
            count += 1
            continue
        print(f"{key} OK")
        count += 1

    if count == len(queries):
        print("Db initialized successfully")
    else:
        print("Failed to create one or more tables")

if len(sys.argv) < 3:
    raise ValueError("Missing one or more required command line argument(s)")

if sys.argv[1] == 'osenv':
    url = os.environ['DATABASE_URL']
else:
    url = sys.argv[1]

if sys.argv[2] == 'init':
    asyncio.get_event_loop().run_until_complete(init(url))