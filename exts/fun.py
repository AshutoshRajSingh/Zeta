import time
import random
import discord
import asyncio
from main import Zeta
from discord.ext import commands
from util import pokemon


class Fun(commands.Cog):
    """
    General commands for getting memes, cute animol pics and much more!
    """

    def __init__(self, bot: Zeta):
        self.bot = bot
        self._subreddit_cache = {}

        # temporary hardcoded value of the id of the latest xkcd comic, updates initially on bot start, then subsequently
        # every time the get_latest_xkcd function is called
        self.mrx: int = 2000
        self.bot.loop.create_task(self.get_latest_xkcd())

        # Create pokeclient
        self.pokeclient = pokemon.Client(session=self.bot.cs)

    async def get_latest_xkcd(self):
        BASE = 'https://xkcd.com/'
        ROUTE = BASE + 'info.0.json'
        async with self.bot.cs.get(ROUTE) as r:
            if r.status != 200:
                return -1
            d = await r.json()
            self.mrx = d.get('num')
            return d

    async def clear_cache_entry(self, entry):
        """
        Does what it says after a fuse of five minutes
        """
        await asyncio.sleep(5 * 60)
        del (self._subreddit_cache[entry])

    @commands.command(aliases=['r'])
    async def reddit(self, ctx: commands.Context, subreddit: str):
        """
        Fetches a random hot image-post from a subreddit.
        Doesn't send any post marked nsfw. Rapid use will cause repetition duh, posts take time to reach hot.
        """
        BASE = 'https://reddit.com'
        ROUTE = BASE + '/r/%s.json'

        start = time.time()

        if subreddit not in self._subreddit_cache:
            async with self.bot.cs.get(ROUTE % subreddit) as r:
                d = await r.json()
                self._subreddit_cache[subreddit] = d

                # Clears the cache entry for the subreddit after 5 minutes so content can stay fresh
                self.bot.loop.create_task(self.clear_cache_entry(subreddit))
        else:
            d = self._subreddit_cache[subreddit]

        # Count the number of nsfw/video posts in the subreddit as they don't go to discord
        nsfw = 1
        video = 1
        misc_invalid = 1

        # Max number of searches to do
        MAX_LOOKUPS = 25

        # The reddit json api doesn't (seem to) return a 404 if subreddit doesn't exist, this seems like a workaround
        # To check if the sub doesn't exist/is private
        if len(d['data']['children']) == 0:
            await ctx.send("Subreddit not found! It may be private or might not exist.")
            return

        # This bit makes sure that the selected post is not a video/marked nsfw, basically keeps choosing a post
        # randomly up to a specified limit : MAX_LOOKUPS until a proper image post is hit.
        else:
            posts = d['data']['children']
            while nsfw < MAX_LOOKUPS and video < MAX_LOOKUPS and misc_invalid < MAX_LOOKUPS:
                selected = random.choice(posts)
                if selected['data'].get('url_overridden_by_dest') is None:
                    misc_invalid += 1
                    continue
                if selected['data']['over_18']:
                    nsfw += 1
                    continue
                if selected['data']['is_video'] or selected['data']['url_overridden_by_dest'].startswith(
                        'https://v.redd.it/'):
                    # To make the command compatible with video posts, here you probably can send the video url in the channel
                    # embeds do not support videos so I decided to not do this as I wanted video to be in embed too.
                    # Haven't tried just sending the video url into the channel thought it probably might work.
                    video += 1
                    continue
                # Imgur support, apparently u just need to yeet .jpg at the end and it automatically redirects you.
                if selected['data']['url_overridden_by_dest'].startswith('https://imgur.com/'):
                    selected['data']['url_overridden_by_dest'] += 'jpg'

                # We take the most "relevant" image formats :shrug:
                if selected['data']['url_overridden_by_dest'].endswith(('jpg', 'png')):
                    e = discord.Embed(title=selected['data']['title'],
                                      url=BASE + selected['data']['permalink'],
                                      colour=discord.Colour(0xFFB6C1))
                    e.set_image(url=selected['data']['url_overridden_by_dest'])

                    duration = time.time() - start
                    e.set_footer(text=f'Requested by {ctx.author}, fetched in %.2gs' % duration,
                                 icon_url=ctx.author.avatar_url)

                    await ctx.send(embed=e)
                    return

            # Send apropriate error message
            if nsfw >= MAX_LOOKUPS:
                await ctx.send(f"Seems like you gave me an nsfw subreddit, can't post.")
            elif video >= MAX_LOOKUPS:
                await ctx.send(f"Seems like you gave me a video only subreddit, can't post.")
            elif misc_invalid >= MAX_LOOKUPS:
                await ctx.send(f'Seems like you gave me a text based subreddit, can\'t post')

    @commands.command(aliases=['doggo', 'doge'])
    async def dog(self, ctx: commands.Context):
        """
        Sends a picture of a random dog.
        """
        BASE = 'https://random.dog'
        ROUTE = '/woof.json'
        async with self.bot.cs.get(BASE + ROUTE) as r:
            d = await r.json()

        e = discord.Embed(title="Random dog",
                          colour=discord.Colour(0xFFB6C1))
        e.set_image(url=d.get('url'))
        if d.get('url').endswith(('.mp4', 'webm')):
            await ctx.send(d.get('url'))
            return
        await ctx.send(embed=e)

    @commands.command(aliases=['catto', 'cate'])
    async def cat(self, ctx: commands.Context):
        """
        Sends a picture of a random cat.
        """
        BASE = 'http://aws.random.cat'
        ROUTE = '/meow'
        async with self.bot.cs.get(BASE + ROUTE) as r:
            d = await r.json()

        e = discord.Embed(title="Random cat",
                          colour=discord.Colour(0xFFB6C1))
        e.set_image(url=d.get('file'))
        if d.get('file').endswith(('.mp4', 'webm')):
            await ctx.send(d.get('file'))
            return
        await ctx.send(embed=e)

    @commands.group(invoke_without_command=True)
    async def xkcd(self, ctx: commands.Context, ComicId: int):
        """
        Sends an xkcd comic strip with the id provided

        `ComicId` here is the id of the comic you wish to fetch, has to be a number duh.
        Has subcommands that provide additional functionality, read up below.
        """
        BASE = 'https://xkcd.com/'
        ROUTE = BASE + '%d/info.0.json'
        async with self.bot.cs.get(ROUTE % ComicId) as r:
            if r.status != 200:
                return await ctx.send("No xkcd found")
            d = await r.json()
        await ctx.send(
            embed=discord.Embed(title=d.get('title'), colour=self.bot.Colour.light_pink(),
                                url=BASE + str(ComicId)).set_image(url=d.get('img')))

    @xkcd.command(aliases=['latest'])
    async def current(self, ctx: commands.Context):
        """
        Sends the current latest xkcd comic.
        """
        d = await self.get_latest_xkcd()
        if d == -1:
            return await ctx.send('An http error occurred')
        await ctx.send(
            embed=discord.Embed(title=d.get('title'), colour=self.bot.Colour.light_pink(),
                                url='https://xkcd.com/%d' % d.get('num')).set_image(url=d.get('img')))
        self.mrx = d.get('num')

    @xkcd.command()
    async def random(self, ctx: commands.Context):
        """
        Sends a random xkcd comic.
        """
        # works cuz stores the number (id) of current latest comic whenever the xkcd latest command is called, then makes
        # a random choice between 1 and that number to avoid overflow.
        return await self.xkcd(ctx, random.randint(1, self.mrx))

    @commands.group(aliases=['dex'], invoke_without_command=True)
    async def pokedex(self, ctx: commands.Context, *, name: str):
        """
        Shows information about a pokemon

        `name` here is the name of the pokemon you wish to view.
        """
        try:
            pokeobj = await self.pokeclient.get_pokemon(name)
            desc = random.choice(pokeobj.species.flavor_text_entries)
            e = discord.Embed(title=pokeobj.name.capitalize(),
                              description=(" ".join(desc.split('\n'))).capitalize(),
                              colour=discord.Colour.random())
            e.add_field(name="ID", value=str(pokeobj.id))
            e.add_field(name="Abilities", value=", ".join(pokeobj.abilities))
            e.add_field(name="Types", value=", ".join(pokeobj.types))
            e.add_field(name="Evolves from", value=str(pokeobj.species.evolves_from))
            e.add_field(name="Growth rate", value=pokeobj.species.growth_rate)
            if pokeobj.species.legendary:
                e.add_field(name="Special", value="Legendary pokemon")
            if pokeobj.species.mythical:
                e.add_field(name="Special", value="Mythical pokemon")
            e.set_image(url=pokeobj.official_artwork)
            await ctx.send(embed=e)
        except pokemon.NoSingleMatch as e:
            await ctx.send(f"Pokemon not found, perhaps you meant one of these:\n{', '.join(e.guesses)}")

    @pokedex.command()
    async def combat(self, ctx: commands.Context, *, name: str):
        """
        Displays a pokemon's combat information

        `name` is the name of the pokemon whose combat info you wish to view.
        """
        try:
            pokeobj = await self.pokeclient.get_pokemon(name)
            e = discord.Embed(title=f"{pokeobj.name.capitalize()}",
                              description=f", ".join(pokeobj.moves),
                              colour=discord.Colour.random())

            e.description += "\n\n**Base stats:**"
            for item in pokeobj.stats:
                e.add_field(name=item['stat']['name'],
                            value=item['base_stat'])
            e.set_thumbnail(url=pokeobj.official_artwork)

            for typename in pokeobj.types:
                _type = await self.pokeclient.fetch_pokemon_type(typename)
                for elem, val in _type.damage_relations.items():
                    if val:
                        e.add_field(name=f"Type ({_type.name}) {' '.join(elem.split('_'))} type(s)",
                                    value=(f", ".join(val)).capitalize(),
                                    inline=False)
            await ctx.send(embed=e)
        except pokemon.NoSingleMatch as e:
            return await ctx.send(f"Pokemon not found, perhaps you meant one of these:\n{', '.join(e.guesses)}")

    @pokedex.command()
    async def evolution(self, ctx: commands.Context, *, name: str):
        """
        Shows the evolution stages of a pokemon

        `name` here is the name of the pokeomn whose evolution you wish to view
        """
        pokeobj = await self.pokeclient.get_pokemon(name)
        if type(pokeobj) is list:
            return await ctx.send(f"Pokemon not found, perhaps you meant one of these:\n{', '.join(pokeobj)}")
        else:
            e = discord.Embed(title=f"{pokeobj.name.capitalize()} evolution",
                              description=f"```\n{pokeobj.species.evolution}```",
                              colour=discord.Colour.random())
            e.set_thumbnail(url=pokeobj.official_artwork)
            await ctx.send(embed=e)

    @pokedex.command()
    async def type(self, ctx: commands.Context, *, name: str):
        """
        Shows the damage relations for a particular type

        `name` here is the name of the type you wish to see the details, for example: fire, electric, water etc.
        """
        typeobj = await self.pokeclient.fetch_pokemon_type(name.lower())
        if typeobj:
            pokeobj = await self.pokeclient.fetch_pokemon(random.choice(typeobj.pokemon))
            e = discord.Embed(title=f"{typeobj.name.capitalize()} type details",
                              description=f"Example pokemon: **{pokeobj.name.capitalize()}**",
                              colour=discord.Colour.random())
            e.set_thumbnail(url=pokeobj.official_artwork)
            for k, v in typeobj.damage_relations.items():
                if v:
                    e.add_field(name=(" ".join(k.split('_'))).capitalize(),
                                value=(", ".join(v)).capitalize(),
                                inline=True)
            await ctx.send(embed=e)
        else:
            return await ctx.send("Pokemon type not found, please double check the spelling")

    @pokedex.command()
    async def move(self, ctx: commands.Context, *, name: str):
        """
        Shows information about a pokemon move

        `name` here is the name of the move you wish to see info about
        """

        try:
            moveobj = await self.pokeclient.get_pokemon_move(name)
            e = discord.Embed(title=f"{moveobj.name.capitalize()}",
                              description=f"{moveobj.effect_entry.splitlines()[0]}",
                              colour=discord.Colour.random())
            e.add_field(name="Accuracy",
                        value=f"{moveobj.accuracy}")
            e.add_field(name="Power",
                        value=f"{moveobj.power}")
            e.add_field(name="Type",
                        value=f"{moveobj.type_name.capitalize()}")
            e.add_field(name=f"Double effectiveness against",
                        value=f"{(', '.join(moveobj.type.double_damage_to) if moveobj.type.double_damage_to else 'None')}".capitalize())
            e.add_field(name=f"Half effectiveness against",
                        value=f"{(', '.join(moveobj.type.half_damage_to)) if moveobj.type.half_damage_to else 'None'}".capitalize())
            e.add_field(name=f"Ineffective against",
                        value=f"{(', '.join(moveobj.type.no_damage_to)) if moveobj.type.no_damage_to else 'None'}".capitalize())
            await ctx.send(embed=e)
        except pokemon.NoSingleMatch as e:
            return await ctx.send(f"Move not found, perhaps you meant one of these:\n{', '.join(e.guesses)}")

def setup(bot: Zeta):
    bot.add_cog(Fun(bot))
