from discord.ext import commands
import __main__


def is_owner_check(ctx):
    return str(ctx.message.author.id) in __main__.amethyst.owners


def instance_owner():
    return commands.check(is_owner_check)
