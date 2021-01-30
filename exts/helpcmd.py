import discord
from discord.ext import commands

"""In hindsight it seemed like a good idea now I regret every single aspect of this implementation, might change it."""


@commands.group(invoke_without_command=True)
async def help(ctx: commands.Context):
    text = f"""```
Use {ctx.prefix}help command_name to get info about that command
        
{ctx.prefix}level   :   Used to show own or someone else's level
{ctx.prefix}lb      :   Used to display server leaderboard 
{ctx.prefix}setbd   :   Saves own birthday in the bot
{ctx.prefix}bday    :   Sends a member's birthday as message
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


@help.command()
async def setbd(ctx: commands.Context):
    text = f"""```
Command used to store your birthday in the bot so other server members can see it

Usage:
{ctx.prefix}setbd date

Date here is your date of birth, the only acceptable format is: DD MM YYYY    
```"""
    embed = discord.Embed(title="setbd",
                          description=text,
                          colour=discord.Colour.blue())
    await ctx.send(embed=embed)


@help.command()
async def bday(ctx: commands.Context):
    text = f"""```
Command that sends a member's birthday as a message, if they have saved it using the {ctx.prefix}setbd command in this server

Usage:
{ctx.prefix}bday target

target here is the member whose birthday you wish to see, can be username, id or mention.
```"""
    embed = discord.Embed(title="bday",
                          description=text,
                          colour=discord.Colour.blue())
    await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_command(help)
