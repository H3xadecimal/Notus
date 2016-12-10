import discord
from discord.ext import commands


class Xeili(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        self.owner = None

    async def on_ready(self):
        print('Ready.')
        print('You are running on a VERY EARLY INCOMPLETE BUILD of Xeili, Do not Report any bugs as it will be fixed.')
        print(xeili.user.name)
        xeili.load_extension('fragments.compact')

    async def on_command_error(self, exception, context):
        channel = context.message.channel
        if isinstance(exception, commands.errors.CommandNotFound):
            await xeili.send_message(channel, "Invalid command... If you were trying to use a command anyway.")
        if isinstance(exception, commands.errors.MissingRequiredArgument):
            await xeili.send_cmd_help(context)

    async def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            _help = xeili.formatter.format_help_for(ctx, ctx.invoked_subcommand)
        else:
            _help = xeili.formatter.format_help_for(ctx, ctx.command)
        for page in _help:
            # noinspection PyUnresolvedReferences
            await xeili.send_message(ctx.message.channel, page)


def get_owner():
    return xeili.owner
            
xeili = Xeili('.')
xeili.run('token')
