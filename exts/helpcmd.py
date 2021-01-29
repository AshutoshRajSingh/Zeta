import discord
from discord.ext import commands


@commands.group(invoke_without_command=True)
async def help(ctx: commands.Context):
    text = f"""```
Use {ctx.prefix}help command_name to get info about that command
        
{ctx.prefix}level   :   Used to show own or someone else's level
{ctx.prefix}lb      :   Used to display server leaderboard 
```"""
    embed = discord.Embed(title="Commands",
                          description=text,
                          colour=discord.Colour.green())
    await ctx.send(embed=embed)


@help.command()
async def level(ctx: commands.Context):
    text = f"""```
Command used to display own or someone else's level
    
Usage:
{ctx.prefix}level target
    
target here is the member whose level you wish to know (can be mention, id or username), if no target specified, own level is shown
```"""
    embed = discord.Embed(title="level",
                          description=text,
                          colour=discord.Colour.blue())
    await ctx.send(embed=embed)


@help.command()
async def lb(ctx: commands.Context):
    text = f"""```
Command used to display top 10 members with the highest exp points

Usage:
{ctx.prefix}lb
```"""
    embed = discord.Embed(title="lb",
                          description=text,
                          colour=discord.Colour.blue())
    await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_command(help)
