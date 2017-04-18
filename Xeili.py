import discord
from discord.ext import commands
from utils.dataIO import dataIO
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
token = config.get('XEILI_TOKEN')
prefix = config.get('XEILI_PREFIX')

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
        self.settings = dataIO.load_json('settings')
        self.blacklist_check = self.loop.create_task(self.blacklist_check())

    async def blacklist_check(self):
        if 'blacklist' not in self.settings:
            self.settings['blacklist'] = []
        else:
            pass

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
             exception = exception.original
             _traceback = traceback.format_tb(exception.__traceback__)
             _traceback = ''.join(_traceback)
             error = '`{0}` in command `{1}`: ```py\nTraceback (most recent call last):\n{2}{0}: {3}\n```'\
                 .format(type(exception).__name__, context.command.qualified_name, _traceback, exception)
             await context.send(error)
        elif isinstance(exception, commands.errors.CommandNotFound):
             pass

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id in self.settings['blacklist']:
            return
        await self.process_commands(message)

async def send_cmd_help(self, ctx):
    if ctx.invoked_subcommand:
        _help = await ctx.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
    else:
        _help = await ctx.bot.formatter.format_help_for(ctx, ctx.command)
    for page in _help:
        # noinspection PyUnresolvedReferences
        await ctx.send(page)


xeili = Xeili(prefix, args, redis_conn)
xeili.run(token)
