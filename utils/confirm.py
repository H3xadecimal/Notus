from discord.ext import commands


def is_owner_check(ctx):
    return ctx.message.author.id == "ID"


def instance_owner():
    return commands.check(is_owner_check)