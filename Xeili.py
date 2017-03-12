import discord
from discord.ext import commands
from utils import dataIO
import asyncio
import traceback
import discord.errors
import redis
import os
import argparse
import json

with open("config.json") as f:
    config = json.load(f)

redis_host = config.get('XEILI_REDIS_HOST') or 'localhost'
redis_pass = config.get('XEILI_REDIS_PASSWORD')
redis_port = int(config.get('XEILI_REDIS_PORT') or 6379)
redis_db = int(config.get('XEILI_REDIS_DB') or 0)

# CMD-L Arguments
parser = argparse.ArgumentParser()
redis_grp = parser.add_argument_group('redis')
redis_grp.add_argument('--host', type=str, help='the Redis host', default=redis_host)
redis_grp.add_argument('--port', type=int, help='the Redis port', default=redis_port)
redis_grp.add_argument('--db', type=int, help='the Redis database', default=redis_db)
redis_grp.add_argument('--password', type=str, help='the Redis password', default=redis_pass)
args = parser.parse_args()

# Redis Connection Attempt... hopefully works.
try:
    redis_conn = redis.StrictRedis(host=args.host, port=args.port, db=args.db, password=args.password)
except:
    print('aaaaaaa unable to redis 404')
    exit(2)


class Xeili(commands.Bot):
    def __init__(self, command_prefix, args, redis, **options):
        super().__init__(command_prefix, **options)
        self.args = args
        self.redis = redis

    async def on_ready(self):
        self.redis.set('__info__', 'This database is being used by the Xeili Framework.')
        print('Ready.')
        print(self.user.name)

        self.load_extension('modules.compact')

    async def on_command_error(self, exception, context):
        channel = context.message.channel
        if isinstance(exception, commands.errors.CommandNotFound):
            pass
        if isinstance(exception, commands.errors.MissingRequiredArgument):
            await self.send_cmd_help(context)
        elif isinstance(exception, commands.errors.CommandInvokeError):
            # Thanks for the code Pand <3
            tb = traceback.format_exc()
            error = '`{0}` in command `{1}`: ```py\n{2}\n```'\
                .format(type(exception).__name__, context.command.qualified_name, tb)
            try:
                await self.send_message(context.message.channel, error)
            except:
                print("Traceback too long!")
                await self.send_message(context.message.channel, "An error occured executing command: {}"\
                    .format(context.command.qualified_name))

async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        _help = ctx.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
    else:
        _help = ctx.bot.formatter.format_help_for(ctx, ctx.command)
    for page in _help:
        # noinspection PyUnresolvedReferences
        await ctx.bot.send_message(ctx.message.channel, page)

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)


xeili = Xeili('test ', args, redis_conn)
xeili.run('token')
