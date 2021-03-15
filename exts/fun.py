import time
import random
import aiohttp
import discord
from discord.ext import commands


class Fun(commands.Cog):
    """
    General commands for getting memes, cute animol pics and much more!
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['r'])
    async def reddit(self, ctx: commands.Context, subreddit: str):
        """
        Fetches a random hot post from a subreddit
        Only works for image posts duh, and doesn't send any posts marked nsfw in the channel
        """
        BASE = 'https://reddit.com'
        ROUTE = BASE + '/r/%s.json'

        start = time.time()

        async with aiohttp.ClientSession() as cs:
            async with cs.get(ROUTE % subreddit) as r:
                d = await r.json()

        # Count the number of nsfw/video posts in the subreddit as they don't go to discord
        nsfw = 1
        video = 1

        # Max number of posts to look up
        MAX_LOOKUPS = 25

        # The reddit json api doesn't (seem to) return a 404 if subreddit doesn't exist, this seems like a workaround
        # To check if the sub doesn't exist/is private
        if len(d['data']['children']) == 0:
            await ctx.send("Subreddit not found! It may be private or might not exist.")
            return
        # There was an attempt to ignore video/nsfw posts however for the video part, if the sub is a video only sub
        # bad things happen and I really am not in the mood to investigate what's wrong (apparently the is_video bool
        # is incorrect for some posts)
        else:
            posts = d['data']['children']
            while nsfw < MAX_LOOKUPS and video < MAX_LOOKUPS:
                selected = random.choice(posts)
                if selected['data']['over_18']:
                    nsfw += 1
                    continue
                if selected['data']['is_video']:
                    video += 1
                    continue

                e = discord.Embed(title=selected['data']['title'],
                                  url=BASE+selected['data']['permalink'],
                                  colour=discord.Colour.red())
                e.set_image(url=selected['data']['url_overridden_by_dest'])

                duration = time.time()-start
                e.set_footer(text=f'Requested by {ctx.author}, fetched in %.2gs' % duration,
                             icon_url=ctx.author.avatar_url)

                await ctx.send(embed=e)
                return

            if nsfw >= MAX_LOOKUPS:
                await ctx.send(f"Looked up {MAX_LOOKUPS} posts, all were nsfw, not posting")
            elif video >= MAX_LOOKUPS:
                await ctx.send(f"Looked up {MAX_LOOKUPS} posts, all were videos, can't post.")


def setup(bot: commands.Bot):
    bot.add_cog(Fun(bot))