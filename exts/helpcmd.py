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
    'giveexp': [
        '(Mod) Used to award a certain amount of exp to a member',
        "giveexp target amount",
        '`target` here is the member who you wish to give exp points to\n'
        '`amount` is the number of exp points you wish to award that person'
    ],
    'setmultiplier': [
        "(Mod) Used to set exp multiplier of a member",
        "setmultiplier target multiplier",
        "`target` here is the member whose multiplier you wish to set, can be mention, id or username\n"
        "`multiplier` here is the exp multiplier you want to set, a value of 2 will indicate twice as fast levelling"
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
    ],
    'lockdown': [
        "(Mod) Initiate a server wide message lockdown",
        "lockdown",
        f"Prevents the `@everyone` role from sending messages/adding reactions in the guild, useful in the event of"
        f"a raid"
    ],
    'unlock': [
        "(Mod) Lifts the lockdown (if any)",
        "unlock",
        "Makes it so that the `everyone` role has the permission to send messages and add reactions in the guild."
    ],
    'mute': [
        "(Mod) Mutes a member preventing them from sending messages/adding reactions in the server",
        "mute target duration",
        "Target here is the member you'd like to mute, duration is the time you wish to mute them for, the only "
        "acceptable format for time is shown by the example: \n`1d 2h 4m`\n"
        "Therefore setting the duration to `1d 2h 4m` would mute your target for 1 day, 2 hours and 4 minutes"
    ],
    'unmute': [
        "(Mod) Unmutes an already muted member, allowing them to send messages/add reactions",
        "unmute target",
        "target here is the member you wish to unmute, note that unmuting a member with a timed mute will end their "
        "mute period at that instant"
    ],
    'bdalerttime': [
        "(Admin) Sets the time at which the bot will send out birthday alerts in the server",
        "bdalerttime time",
        "`time` here is the time at which you want birthday alerts to be sent out on your server, it has to be in UTC, "
        "and the ony acceptable format is `HH MM` where HH is hours of the day (in 24h format) and MM is the minutes "
        "of the day"
    ],
    'tag': [
        'Retrieves an earlier stored tag',
        'tag tagname',
        'tagname here is the name of the tag you wish to fetch, for example to get a tag named '
        '\'boop\' you would use `tag boop` ',
        ['create', 'edit', 'delete']
    ],
    'tag create': [
        'Stores text for later retreival',
        'tag create tagname content',
        'tagname here is the name you wish the new tag to have content here is the text you wish to store, for example to '
        'store the text "spaghetti" under the tagname "pasta"'
        ' you would use `tag create pasta spaghetti`'
    ],
    'tag edit': [
        'Edits a tag owned by you',
        'tag edit tagname newcontent',
        'tagname is the name of the tag you wish to edit, newcontent is the text you wish to replace it with, note that '
        'you can only edit tags you own'
    ],
    'tag delete': [
        'Deletes a tag already created by someone',
        'tag delete tagname',
        "tagname here is the name of the tag you wish to delete, if you own it, you can delete it straightforwardly, if you don't you "
        "will need the server permission 'Manage messages' in order to delete it."
    ],
    'reddit': [
        'Used to get a random post from a subreddit',
        'reddit subreddit_name',
        'subreddit_name here is the name of the subreddit from which you wish to get a post\n'
        'Alternate names for this command: `r`'
    ],
    'r': [
        'Used to get a random post from a subreddit',
        'reddit subreddit_name',
        'subreddit_name here is the name of the subreddit from which you wish to get a post\n'
        'Alternate names for this command: `r`'
    ],
    'reacrole': [
        'The base command to configure reaction roles, doesn\'t do anything by itself, you need to use the subcommand '
        'for each action',
        'reacrole subcommand',
        'Nothing here',
        ['create',]
    ],
    'reacrole create': [
        'Create a reaction roles menu',
        'reacrole create title role1 role2 role3...',
        'role1, role2, role3 are the roles you wish to create the menu for, can be any number, you can enter the id of'
        ' the roles, their name (enclosed in double quotes if it has a space), or their mention\nTitle is the title of'
        ' the role menu that will show up on the top. The first argument is always title\n'
        'After you use this command it will guide you through creating the menu, including what reactions correspond'
        ' to what role and which channel you want to put the role menu in.'
    ]
}

categoryinfo = {
    "Level System": [
        'level', 'lb', 'giveexp', 'setmultiplier'
    ],
    "Birthday system": [
        'setbd', 'bday', 'bdchannel', 'bdalerttime'
    ],
    "Utility": [
        'tag', 'reddit'
    ],
    "Moderation": [
        'lockdown', 'unlock', 'mute', 'unmute'
    ],
    "Admin": [
        'prefix', 'reacrole'
    ],
}


@commands.command()
async def help(ctx: commands.Context, *, arg: str = None):
    if not arg:
        title = "Commands"
        text = ""
        embed = discord.Embed(title=title,
                              description=f"Use {ctx.prefix}help command for more info on a command\n"
                                          f"Use {ctx.prefix}help command subcommand for more info on a subcommand\n",
                              colour=discord.Colour.green())
        for category in categoryinfo:
            for command in categoryinfo[category]:
                text += f"`{command}`, "
            embed.add_field(name=category, value=text[:len(text)-2], inline=True)
            text = ""
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
        if len(data) == 4:
            embed.description += "\n**Subcommands:**\n"
            for elem in data[3]:
                embed.add_field(name=elem, value=everything[f"{arg} {elem}"][0])

    await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_command(help)
