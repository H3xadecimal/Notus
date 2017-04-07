import discord
from discord.ext import commands
from utils import confirm
from __main__ import send_cmd_help
from utils.dataIO import dataIO


class utilities:
    def __init__(self, xeili):
        self.xeili = xeili
        self.settings = dataIO.load_json('settings')
        self.database_checks = self.xeili.loop.create_task(self.db_check())

    def __unload(self):
        self.database_checks.cancel()

    async def db_check(self):
        if 'owners' not in self.settings:
            self.settings['owners'] = []
        else:
            pass

    @commands.command()
    async def ping(self):
        """Pong."""
        await self.xeili.say("Pong.")

    @commands.group(name="set", pass_context=True, invoke_without_subcommand=True)
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

    @utils_set.command(name="owner", pass_context=True)
    async def utils_set_owner(self, user: discord.Member):
        """Sets other owners."""
        self.settings['owners'].append(user.id)
        await self.xeili.say("User set as owner.")

    @commands.group(name="blacklist", pass_context=True, invoke_without_subcommand=True)
    @confirm.instance_owner()
    async def blacklist_commands(self, ctx):
        """Prevents a user from using the bot globally."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @blacklist_commands.command(name="add", pass_context=True)
    async def add_blacklist(self, ctx, user: discord.Member):
        """Adds a user to blacklist."""
        if user.id not in self.settings['blacklist']:
            try:
                self.settings['blacklist'].append(user.id)
                await self.xeili.say("User blacklisted.")
            except:
                await self.xeili.say("An error occured.")
        else:
            await self.xeili.say("User already blacklisted.")

    @blacklist_commands.command(name="remove", pass_context=True)
    async def remove_blacklist(self, ctx, user: discord.Member):
        """Removes a user from blacklist."""
        if user.id not in self.settings['blacklist']:
            await self.xeili.say("User is not blacklisted.")
        else:
            self.settings['blacklist'].remove(user.id)
            await self.xeili.say("User removed from blacklist.")


def setup(xeili):
    xeili.add_cog(utilities(xeili))
