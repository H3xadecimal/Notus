import discord
from discord.ext import commands


class basic:
    """Module to test cog loading."""
    def __init__(self, xeili):
        self.xeili = xeili

    @commands.command()
    async def ping(self):
        """Pong."""
        await self.xeili.say("Pong.")


def setup(xeili):
    xeili.add_cog(basic(xeili))
