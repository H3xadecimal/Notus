import asyncio
import mimetypes
from typing import TYPE_CHECKING, List

import discord
from discord.ext import commands

from utils import check

if TYPE_CHECKING:
    from notus import Notus


class MultiStringConverter(commands.Converter):
    def __init__(self, *strings: List[str]):
        self.strings = strings

    async def convert(self, ctx, arg):
        if arg not in self.strings:
            raise commands.BadArgument(f"Must be one of `{','.join(self.strings)}`")
        else:
            return arg


class Utilities(commands.Cog):
    def __init__(self, notus: Notus):
        self.notus = notus

    @property
    def settings(self):
        return self.notus.db["settings"]

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Pong"""
        await ctx.send("Pong.")

    @commands.group("set", invoke_without_command=True)
    @check.owner()
    async def set_(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @set_.command("nickname", aliases=["nick"])
    @check.permissions.me(discord.Permissions(change_nickname=True))
    async def set_nickname(self, ctx: commands.Context, nickname: str):
        """Set the bot's nickname"""
        if len(nickname) > 32:
            return await ctx.send("Nickname is too long. Limit is 32 characters.")

        try:
            await ctx.me.edit(nickname=nickname)
            await ctx.send(":thumbsup:")
        except Exception:
            await ctx.send("Failed to change nickname. :shrug:")

    @set_.command("game")
    async def set_game(self, ctx: commands.Context, game: str):
        """Set the bot's game"""
        pass

    @set_.command("status")
    async def set_status(
        self,
        ctx: commands.Context,
        status: MultiStringConverter("online", "dnd", "idle", "invisible"),
    ):
        """Set the bot's status"""
        status = getattr(discord.Status, status)

        await self.notus.change_presence(status=status)
        await ctx.send(":thumbsup:")

    @set_.command("avatar")
    async def set_avatar(self, ctx, url: str = None):
        """Set the bot's avatar"""
        if not url and not ctx.message.attachments:
            return await ctx.send("Please give an avatar URL or as an attachment")
        elif not url:
            url = ctx.message.attachments[0].url

        ext = url.split(".")[-1]
        mime = mimetypes.types_map.get(ext)

        if mime not in ("image/png", "image/jpeg", "image/webp"):
            return await ctx.send(f"Unsupported mimetype `{mime}`")

        async with ctx.typing():
            async with self.notus.session.get(url) as resp:
                data = await resp.read()

            try:
                await self.notus.user.edit(avatar=data)
            except Exception:
                return await ctx.send("Failed to set avatar.")

        await ctx.send(":thumbsup:")

    @commands.group(invoke_without_command=True)
    @check.owner()
    async def blacklist(self, ctx: commands.Context):
        """Prevent a user from using the bot at all"""
        await ctx.send_help(ctx.command)

    @blacklist.command("list")
    async def blacklist_list(self, ctx: commands.Context):
        """List all currently blacklisted users"""
        users = [self.notus.get_user(x) or x for x in self.settings["blacklist"]]

        for i, user in enumerate(users):
            if not isinstance(user, int):
                pass

            try:
                user = await self.notus.fetch_user(user)
                users[i] = user
            except discord.DiscordException:
                users[i] = f"**Unknown user** ({user})"

        users = [
            (
                f"**{user.name}#{user.discriminator}** ({user.id})"
                if isinstance(x, discord.User)
                else x
            )
            for x in users
        ]

        await ctx.send("__Currently blacklisted users__\n" + "\n".join(users))

    @blacklist.command("add")
    async def blacklist_add(self, ctx: commands.Context, user: discord.User):
        """Add a user to the blacklist"""
        if user.id in self.settings["blacklist"]:
            return await ctx.send("User already blacklisted.")

        self.settings["blacklist"].append(user.id)
        await ctx.send("User blacklisted.")

    @blacklist.command("remove")
    async def blacklist_remove(self, ctx: commands.Context, user: discord.User):
        """Remove a user from the blacklist"""
        if user.id not in self.settings["blacklist"]:
            return await ctx.send("User is not blacklisted")

        self.settings["blacklist"].remove(user.id)
        await ctx.send("User removed from blacklist.")

    @commands.command(aliases=["clean"])
    @check.guild()
    async def cleanup(self, ctx: commands.Command):
        """Clean up the bot's messages"""
        msgs = await ctx.channel.history(limit=100).flatten()
        msgs = [x for x in msgs if x.author.id == self.notus.user.id]

        if not msgs:
            return

        if ctx.me.permissions_in(ctx.channel).manage_messages:
            await ctx.msg.channel.delete_messages(msgs)
        else:
            for msg in msgs:
                await msg.delete()
                await asyncio.sleep(1.3)  # Try to avoid getting ratelimited


def setup(notus):
    notus.add_cog(Utilities)
