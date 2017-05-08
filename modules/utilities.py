import discord
import asyncio
import aiohttp
import mimetypes
from discord.ext import commands
from utils import confirm
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

    @commands.command()
    async def ping(self, ctx):
        """Pong."""
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
                await ctx.guild.me.edit(nick=name)
                await ctx.send("Beep Boop. Done.")
            else:
                await ctx.send(
                    "Character count is over 32!... Try with less characters.")
        except:
            await ctx.send("Error changing nickname, either "
                           "`Lacking Permissions` or `Something Blew Up`.")

    @utils_set.command(name="game")
    async def utils_set_game(self, ctx, *, game: str=None):
        """Sets Bot's playing status."""
        if game is not None:
            await self.xeili.change_presence(game=discord.Game(name=game))
            await ctx.send("Done.")
        else:
            await self.xeili.change_presence(game=None)
            await ctx.send("Done.")

    @utils_set.command(name="status")
    async def utils_set_status(self, ctx, status: str):
        """Sets bot presence."""
        status = getattr(discord.Status, status, discord.Status.online)
        await self.xeili.change_presence(status=status)
        await ctx.send("Changed status!")

    @utils_set.command(name="owner")
    async def utils_set_owner(self, ctx, user: discord.Member):
        """Sets other owners."""
        self.settings['owners'].append(user.id)
        await ctx.send("User set as owner.")

    @utils_set.command(name="avatar")
    async def utils_set_avatar(self, ctx, url: str=None):
        """ Changes the bots avatar """
        if url is None:
            if not ctx.message.attachments:
                return await ctx.say("No avatar found! "
                                     "Provide an Url or Attachment!")
            else:
                url = ctx.message.attachments[0].get("url")

        ext = url.split(".")[-1]
        mime = mimetypes.types_map.get(ext)
        if mime is not None and not mime.startswith("image"):
            # None can still be an image
            return await ctx.send("Url or Attachment is not an Image!")

        async with aiohttp.ClientSession() as s, s.get(url) as r:
            if 200 <= r.status_code < 300:
                content = await r.read()
            else:
                return await ctx.send("Invalid Response code: {}"
                                      .format(r.status_code))

        try:
            await self.xeili.user.edit(avatar=content)
        except BaseException:  # I don't know the exact Exception type
            return await ctx.send("Avatar was too big or not an image!")

        await ctx.send("Successfully updated avatar!")

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

    @commands.command(aliases=['clean'])
    async def cleanup(self, ctx):
        """Cleans up the bot's messages."""
        msgs = await ctx.message.channel.history(limit=100).flatten()
        msgs = [msg for msg in msgs if msg.author.id == self.xeili.user.id]

        if (len(msgs) > 0 and
                ctx.me.permissions_in(ctx.channel).manage_messages):
            await ctx.channel.delete_messages(msgs)
        elif len(msgs) > 0:
            for msg in msgs:
                await msg.delete()
        else:
            return

        msg = await ctx.send("Cleaned `{}`".format(len(msgs)))
        await asyncio.sleep(2.5)
        await msg.delete()


def setup(xeili):
    xeili.add_cog(utilities(xeili))
