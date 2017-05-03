import discord
from discord.ext import commands
from utils import confirm
from utils.dataIO import dataIO
from random import choice


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
    async def ping(self, ctx):
        """Pokes Ovy."""
        await ctx.send("Pong.")

    @commands.group(name="set", invoke_without_subcommand=True)
    @confirm.instance_owner()
    async def utils_set(self, ctx):
        """Sets various stuff."""
        await self.xeili.send_command_help(ctx)

    @utils_set.command(name="nickname")
    async def utils_set_nickname(self, ctx, *, name: str=None):
        """Sets Bot nickname."""
        try:
            if len(str(name)) < 32:
                await guild.me.edit(nick=name)
                await ctx.send("Beep Boop. Done.")
            else:
                await ctx.send("Character count is over 32!... Try with less characters.")
        except:
            await ctx.send("Error changing nickname, either `Lacking Permissions` or `Something Blew Up`.")

    @utils_set.command(name="game")
    async def utils_set_game(self, ctx, *, game: str=None):
        """Sets Bot's playing status."""
        server = ctx.message.server
        statooos = server.me.status
        if game is not None:
            await self.xeili.change_presence(game=discord.Game(name=game), status=statooos)
            await ctx.send("Done.")
        else:
            await self.xeili.change_presence(game=discord.Game(name=None), status=statooos)
            await ctx.send("Done.")

    @utils_set.command(name="status")
    async def utils_set_status(self, ctx):
        """Sets bot presence."""
        discord_status = 'online', 'invisible', 'idle', 'dnd'
        game = ctx.message.server.me.game
        await ctx.send("This command is incomplete.")

    @utils_set.command(name="owner")
    async def utils_set_owner(self, ctx, user: discord.Member):
        """Sets other owners."""
        self.settings['owners'].append(user.id)
        await ctx.send("User set as owner.")

    @commands.group(name="blacklist", invoke_without_subcommand=True)
    @confirm.instance_owner()
    async def blacklist_commands(self, ctx):
        """Prevents a user from using the bot globally."""
        await self.xeili.send_command_help(ctx)

    @blacklist_commands.command(name="add")
    async def add_blacklist(self, ctx, user: discord.Member):
        """Adds a user to blacklist."""
        if user.id not in self.settings['blacklist']:
            try:
                self.settings['blacklist'].append(user.id)
                await ctx.send("User blacklisted.")
            except:
                await ctx.send("An error occured.")
        else:
            await ctx.send("User already blacklisted.")

    @blacklist_commands.command(name="remove")
    async def remove_blacklist(self, ctx, user: discord.Member):
        """Removes a user from blacklist."""
        if user.id not in self.settings['blacklist']:
            await ctx.send("User is not blacklisted.")
        else:
            self.settings['blacklist'].remove(user.id)
            await ctx.send("User removed from blacklist.")


def setup(xeili):
    xeili.add_cog(utilities(xeili))
