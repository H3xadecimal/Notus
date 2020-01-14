import discord
from discord.ext.commands import check


def owner():
    def checker(ctx):
        return ctx.message.author.id in ctx.bot.owners

    return check(checker)


def guild():
    def checker(ctx):
        return not ctx.is_dm()

    return check(checker)


def roles(*roles: int):
    def checker(ctx):
        return not ctx.is_dm() and len(
            [x for x in ctx.message.author.roles if x.id in roles]
        ) == len(roles)

    return check(checker)


def named_roles(*roles: str):
    def checker(ctx):
        return not ctx.is_dm() and all(
            [x.name in roles for x in ctx.message.author.roles]
        )

    return check(checker)


def nsfw():
    def checker(ctx):
        return (
            isinstance(ctx.message.channel, discord.TextChannel)
            and ctx.message.channel.is_nsfw()
        )

    return check(checker)
