from discord.ext import commands


def is_owner_check(ctx):
    return str(ctx.message.author.id) in ['ID']


def instance_owner():
    return commands.check(is_owner_check)
