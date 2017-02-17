import discord
from discord.ext import commands
import asyncio
import traceback
import discord.errors


class Xeili(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)

    async def on_ready(self):
        print('Ready.')
        print(xeili.user.name)

        xeili.load_extension('modules.compact')

    async def on_command_error(self, exception, context):
        channel = context.message.channel
        if isinstance(exception, commands.errors.CommandNotFound):
            pass
        if isinstance(exception, commands.errors.MissingRequiredArgument):
            await xeili.send_cmd_help(context)
        elif isinstance(exception, commands.errors.CommandInvokeError):
            # Thanks for the code Pand <3
            exception = exception.original
            _traceback = traceback.format_tb(exception.__traceback__)
            _traceback = ''.join(_traceback)
            error = '`{0}` in command `{1}`: ```py\nTraceback (most recent call last):\n{2}{0}: {3}\n```'\
                .format(type(exception).__name__, context.command.qualified_name, _traceback, exception)
            await xeili.send_message(context.message.channel, error)

async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        _help = xeili.formatter.format_help_for(ctx, ctx.invoked_subcommand)
    else:
        _help = xeili.formatter.format_help_for(ctx, ctx.command)
    for page in _help:
        # noinspection PyUnresolvedReferences
        await xeili.send_message(ctx.message.channel, page)

    async def on_message(self, message):
        if message.author.bot:
            return
        await xeili.process_commands(message)

            
xeili = Xeili('test ')
xeili.run('token')
