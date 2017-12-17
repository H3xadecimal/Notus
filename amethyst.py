#!/usr/bin/env python3.6

from discord import utils as dutils
from discord.ext.commands import Paginator
from utils.dataIO import DataManager
from utils import dusk, message_parsing
import utils.arg_converters as arg_converters
import traceback
import redis
import argparse
import json
import discord
import string
import asyncio
import aiohttp

with open("config.json") as f:
    config = json.load(f)

redis_host = config.get('AMETHYST_REDIS_HOST', 'localhost')
redis_pass = config.get('AMETHYST_REDIS_PASSWORD')
redis_port = int(config.get('AMETHYST_REDIS_PORT', 6379))
redis_db = int(config.get('AMETHYST_REDIS_DB', 0))
token = config.get('AMETHYST_TOKEN')
prefixes = config.get('AMETHYST_PREFIXES', [])
tagline = config.get('AMETHYST_TAGLINE', '{} is an instance of Amethyst, learn more about the project at '
                     'https://github.com/awau/Amethyst')

# CMD-L Arguments
parser = argparse.ArgumentParser()
redis_grp = parser.add_argument_group('redis')
redis_grp.add_argument('--host', type=str,
                       help='the Redis host', default=redis_host)
redis_grp.add_argument('--port', type=int,
                       help='the Redis port', default=redis_port)
redis_grp.add_argument('--db', type=int,
                       help='the Redis database', default=redis_db)
redis_grp.add_argument('--password', type=str,
                       help='the Redis password', default=redis_pass)
args = parser.parse_args()

# Redis Connection Attempt... hopefully works.
try:
    redis_conn = redis.StrictRedis(host=args.host,
                                   port=args.port,
                                   db=args.db,
                                   password=args.password)
except:
    print('Unable to connect to Redis.')
    exit(2)


class Amethyst(discord.Client):
    def __init__(self, config, args, redis, **options):
        super().__init__(**options)
        self.args = args
        self.redis = redis
        self.data = DataManager(self.redis)
        self.owner = None
        self.config = config
        self.settings = self.data.load('settings')
        self.blacklist_check = self.loop.create_task(self.blacklist_check())
        self.holder = dusk.CommandHolder(self)
        self.commands = self.holder
        self.converters = arg_converters.Converters(self)
        self.session = aiohttp.ClientSession()
        self.send_cmd_help = self.holder.send_cmd_help
        self.send_command_help = self.send_cmd_help
        self.tagline = tagline

    async def blacklist_check(self):
        if 'blacklist' not in self.settings:
            self.settings['blacklist'] = []
        else:
            pass

    async def on_ready(self):
        self.redis.set('__info__', 'This database is being used by the Amethyst Framework.')

        app_info = await self.application_info()
        self.invite_url = dutils.oauth_url(app_info.id)
        self.owner = str(app_info.owner.id)

        print('Ready.')
        print(self.invite_url)
        print(self.user.name)

        self.holder.load_module('modules.core')

    async def handle_error(self, exception, ctx):
        _traceback = traceback.format_tb(exception.__traceback__)
        _traceback = ''.join(_traceback)
        error = '`{0}` in command `{1}`: ```py\nTraceback (most recent call last):\n{2}{0}: {3}\n```'.format(
                type(exception).__name__, ctx.cmd, _traceback, exception)

        await ctx.send(error)

    async def on_message(self, message):
        if (not message.content or message.author.bot or
                (str(message.author.id) in self.settings['blacklist'] and
                 str(message.author.id) not in self.owners)):
            return

        cleaned = message_parsing.parse_prefixes(message.content, prefixes)

        if (cleaned == message.content or
                cleaned[0] in string.whitespace):
            return

        cmd = message_parsing.get_cmd(cleaned)

        if not self.holder.get_command(cmd):
            return

        ctx = dusk.Context(message, self)

        try:
            await self.holder.run_command(ctx)
        except Exception as e:
            await self.handle_error(e, ctx)


amethyst = Amethyst(config, args, redis_conn)
amethyst.run(token)
