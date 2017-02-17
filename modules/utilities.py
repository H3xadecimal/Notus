import discord
from discord.ext import commands
from utils import confirm
from __main__ import send_cmd_help

class utilities:
    def __init__(self, xeili):
        self.xeili = xeili

    # Custom Errors test.
    async def raise_error_CommandIncomplete(self, ctx):
        await self.xeili.say("This command is incomplete. We're working on it.")
        # This is gonna be used later on, Don't mind it.

    @commands.command()
    async def ping(self):
        """Pong."""
        await self.xeili.say("Pong.")

    @commands.group(name="set", pass_context=True, invoke_without_command=True)
    @confirm.instance_owner()
    async def utils_set(self, ctx):
        """Sets various stuff."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @utils_set.command(name="nickname", pass_context=True)
    async def utils_set_nickname(self, ctx, *, nickname: str=None):
        """Sets Bot nickname."""
        try:
            if len(str(nickname)) < 32:
                await self.xeili.change_nickname(ctx.message.server.me, nickname)
                await self.xeili.say("Beep Boop. Done.")
            else:
                await self.xeili.say("Character count is over 32!... Try with less characters.")
        except:
            await self.xeili.say("Error changing nickname, either `Lacking Permissions` or `Something Blew Up`.")


def setup(xeili):
    xeili.add_cog(utilities(xeili))
