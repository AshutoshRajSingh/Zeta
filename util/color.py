import discord


class Color(discord.Color):
    """
    Colors that aren't part of standard lib colors
    """
    def __init__(self, _hex):
        super().__init__(_hex)

    @classmethod
    def light_pink(cls):
        return cls(0xFFB6C1)


