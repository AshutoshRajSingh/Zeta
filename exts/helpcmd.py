import discord
from discord.ext import commands

everything = {
    'level': [
        'Used to show own or someone else\'s level',
        "level target",
        "target here is the member whose level you wish to know (can be mention, id or username), if no target specified, own level is shown"
    ],
    'lb': [
        "Used to show server leaderboard",
        "lb",
        ""
    ],

    'setbd': [
        "Used to save your own birthday in bot so others can see it",
        "setbd date_of_birth",
        "date_of_birth is the date on which you were born, the only acceptable format is:\n`DD MM YYYY`"
    ],
    'bday': [
        "Used to get a member's birthday",
        "bday target",
        "target here is the member whose birthday you wish to display, can be mention, id or username"
    ],

    'prefix': [
        'Used to set server prefix',
        "prefix new_prefix",
        "new_prefix here is the new server prefix that will be used for commands, can be up to 10 characters long"
    ],
    'bdchannel': [
        "Used to set birthday alert channel",
        "bdaychannel target_channel",
        "target_channel here is the server channel you wish to set for sending out birthday alerts, if not configured,"
        "birthday alerts are not sent out."
    ]

}

categoryinfo = {
    "Level System": [
        'level', 'lb'
    ],
    "Misc": [
        'setbd', 'bday'
    ],
    "Admin": [
        'prefix', 'bdchannel'
    ],
}


@commands.command()
async def help(ctx: commands.Context, arg: str = None):
    if not arg:
        title = "Commands"
        text = ""
        for category in categoryinfo:
            text += f"```{category}```\n"
            for command in categoryinfo[category]:
                text += f"**{command}**\n{everything[command][0]}\n\n"
            text += "\n"
    else:
        data = everything.get(arg)
        if not data:
            await ctx.send(f"Couldn't find the command that you were looking for, please use `{ctx.prefix}help` to get"
                           f" a list of usable commands")
            return
        title = f"Command: {arg}"
        text = f"""
**{data[0]}**

Usage:
```{ctx.prefix}{data[1]}```
{data[2]}        
"""
    embed = discord.Embed(title=title,
                          description=text,
                          colour=discord.Colour.green())
    await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_command(help)
