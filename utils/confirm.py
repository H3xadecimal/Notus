from discord.ext import commands


def is_owner_check(ctx):
    return str(ctx.message.author.id) in ['161866631004422144']


def instance_owner():
    return commands.check(is_owner_check)
