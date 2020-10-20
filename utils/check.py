import discord
from discord.ext.commands import Context, check


def owner():
    """Check if caller is a bot owner"""

    def checker(ctx: Context):
        return ctx.author.id in ctx.bot.owners

    return check(checker)


def guild():
    """Check if called in a guild"""

    def checker(ctx: Context):
        return not ctx.is_dm()

    return check(checker)


def roles(*roles: int):
    """Check if caller has all given roles"""

    def checker(ctx: Context):
        return not ctx.is_dm() and all([x.id in roles for x in ctx.author.roles])

    return check(checker)


def named_roles(*roles: str):
    """Check if caller has all given roles, checking by name"""

    def checker(ctx: Context):
        return not ctx.is_dm() and all([x.name in roles for x in ctx.author.roles])

    return check(checker)


def nsfw():
    """Check if called in a NSFW channel"""

    def checker(ctx: Context):
        return isinstance(ctx.channel, discord.TextChannel) and ctx.channel.is_nsfw()

    return check(checker)


class permissions:
    @staticmethod
    def author(permissions: discord.Permissions):
        """Check if caller has required permissions"""

        def checker(ctx: Context):
            return (
                isinstance(ctx.author, discord.Member)
                and ctx.author.permissions_in(ctx.channel) >= permissions
            )

        return check(checker)

    @staticmethod
    def me(permissions: discord.Permissions):
        """Check if bot has required permissions"""

        def checker(ctx: Context):
            return (
                isinstance(ctx.me, discord.Member)
                and ctx.me.permissions_in(ctx.channel) >= permissions
            )

        return check(checker)
