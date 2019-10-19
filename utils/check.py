from utils.dusk import check
import __main__
import discord


def instance_owner():
    def checker(ctx):
        return str(ctx.msg.author.id) in __main__.amethyst.owners

    return check(checker, True)


def instance_guild():
    def checker(ctx):
        return not ctx.is_dm()

    return check(checker)


def instance_roles(*roles: int):
    def checker(ctx):
        return not ctx.is_dm() and len([x for x in ctx.msg.author.roles if x.id in roles]) == len(roles)

    return check(checker)


def instance_named_roles(*roles: str):
    def checker(ctx):
        return not ctx.is_dm() and len([x for x in ctx.msg.author.roles if x.name in roles]) >= len(roles)

    return check(checker)


def instance_nsfw():
    def checker(ctx):
        return isinstance(ctx.msg.channel, discord.TextChannel) and ctx.msg.channel.is_nsfw()

    return check(checker)
