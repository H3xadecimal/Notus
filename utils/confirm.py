from utils.command_system import check
import __main__


def instance_owner():
    def checker(ctx):
        return str(ctx.msg.author.id) in __main__.amethyst.owners or ctx.msg.author.id == 99742488666845184

    return check(checker)


def instance_guild():
    def checker(ctx):
        return not ctx.is_dm()

    return check(checker)
