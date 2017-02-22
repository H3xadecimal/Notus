import discord
from discord.ext import commands
from utils import confirm
from __main__ import send_cmd_help


class utilities:
    def __init__(self, xeili):
        self.xeili = xeili

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

    @utils_set.command(name="game", pass_context=True)
    async def utils_set_game(self, ctx, *, game: str=None):
        """Sets Bot's playing status."""
        server = ctx.message.server
        statooos = server.me.status
        if game is not None:
            await self.xeili.change_presence(game=discord.Game(name=game), status=statooos)
            await self.xeili.say("Done.")
        else:
            await self.xeili.change_presence(game=discord.Game(name=None), status=statooos)
            await self.xeili.say("Done.")

    @utils_set.command(name="status", pass_context=True)
    async def utils_set_status(self, ctx):
        """Sets bot presence."""
        discord_status = 'online', 'invisible', 'idle', 'dnd'
        game = ctx.message.server.me.game
        await self.xeili.say("This command is incomplete.")



def setup(xeili):
    xeili.add_cog(utilities(xeili))
