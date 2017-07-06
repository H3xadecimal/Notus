from discord import utils as dutils
from discord.ext.commands import Paginator
from utils.dataIO import dataIO
from utils import command_system, message_parsing
import traceback
import redis
import argparse
import json
import discord
import string
import asyncio

with open("config.json") as f:
    config = json.load(f)

redis_host = config.get('AMETHYST_REDIS_HOST') or 'localhost'
redis_pass = config.get('AMETHYST_REDIS_PASSWORD')
redis_port = int(config.get('AMETHYST_REDIS_PORT') or 6379)
redis_db = int(config.get('AMETHYST_REDIS_DB') or 0)
token = config.get('AMETHYST_TOKEN')
prefixes = config.get('AMETHYST_PREFIXES', [])
tagline = config.get('AMETHYST_TAGLINE') or '{} is an instance of Amethyst, learn more about the\
 project at https://github.com/awau/Amethyst'

if config.get('AMETHYST_PREFIX'):
    print('IMPORTANT')
    print('Oldish config detected with key `AMETHYST_PREFIX`')
    print('Due to the new system supporting multiple prefixes, this value is being phased out in favour of '
          '`AMETHYST_PREFIXES`')
    print('The original key will still be added to all prefixes for now, however we cannot guarantee that this will be '
          'around forever, so it is recommended that you switch over to `AMETHYST_PREFIXES`')

    prefixes.append(config.get('AMETHYST_PREFIX'))

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
    print('aaaaaaa unable to redis 404')
    exit(2)


class Amethyst(discord.Client):
    def __init__(self, config, args, redis, **options):
        super().__init__(**options)
        self.args = args
        self.redis = redis
        self.owner = None
        self.config = config
        self.send_command_help = self.send_cmd_help
        self.settings = dataIO.load_json('settings')
        self.blacklist_check = self.loop.create_task(self.blacklist_check())
        self.holder = command_system.CommandHolder(self)

    async def blacklist_check(self):
        if 'blacklist' not in self.settings:
            self.settings['blacklist'] = []
        else:
            pass

    async def send_cmd_help(self, ctx):
        paginator = Paginator()

        if len(ctx.cmd.split(' ')) != 2:
            cmd = self.holder.get_command(ctx.cmd)

            if not cmd:
                return await ctx.send('Unknown command.')

            if cmd.name == 'help':
                longest_cmd = sorted(self.holder.all_commands, key=len, reverse=True)[0]
                modules = set([self.holder.get_command(x).cls.__class__.__name__ for x in self.holder.commands])
                modules = sorted(modules)

                paginator.add_line(tagline.format(self.user.name), empty=True)

                for module in modules:
                    paginator.add_line(module + ':')

                    module_commands = [self.holder.get_command(x) for x in self.holder.commands if
                                       self.holder.get_command(x).cls.__class__.__name__ == module and
                                       not hasattr(self.holder.get_command(x), 'parent')]
                    module_commands = sorted(module_commands, key=lambda x: x.name)

                    for cmd in module_commands:
                        spacing = ' ' * (len(longest_cmd) - len(cmd.name) + 1)
                        line = f'  {cmd.name}{spacing}{cmd.short_description}'

                        if len(line) > 80:
                            line = line[:77] + '...'

                        paginator.add_line(line)

                paginator.add_line('')
                paginator.add_line(f'Type {prefixes[0]}help command for more info on a command.')

                if len(prefixes) > 1:
                    extra_prefixes = ', '.join([f'"{x}"' for x in prefixes[1:]])

                    paginator.add_line(f'Additional prefixes include: {extra_prefixes}')

                for page in paginator.pages:
                    await ctx.send(page, dest='author')
                    await asyncio.sleep(.333)
            else:
                if hasattr(cmd, 'commands'):  # Command is a group. Display main help-like message.
                    longest_cmd = sorted(cmd.commands, key=lambda x: len(x.name), reverse=True)[0].name
                    commands = sorted(cmd.commands, key=lambda x: x.name)

                    paginator.add_line(prefixes[0] + cmd.name, empty=True)
                    paginator.add_line(cmd.description, empty=True)
                    paginator.add_line('Commands:')

                    for command in commands:
                        spacing = ' ' * (len(longest_cmd) - len(command.name) + 1)
                        line = f'  {command.name}{spacing}{command.short_description}'

                        paginator.add_line(line)

                    paginator.add_line('')

                    if cmd.aliases:
                        aliases = ', '.join(cmd.aliases)
                        paginator.add_line(f'Aliases for this command are: {aliases}')

                    paginator.add_line(f'Type {prefixes[0]}{cmd.name} command to run the command.')

                    for page in paginator.pages:
                        await ctx.send(page)
                        await asyncio.sleep(.333)
                else:
                    paginator.add_line(prefixes[0] + cmd.name + ' ' + cmd.usage, empty=True)
                    paginator.add_line(cmd.description)

                    if cmd.aliases:
                        aliases = ', '.join(cmd.aliases)

                        paginator.add_line('')
                        paginator.add_line(f'Aliases for this command are: {aliases}')

                    for page in paginator.pages:
                        await ctx.send(page)
                        await asyncio.sleep(.333)
        else:
            parent = self.holder.get_command(ctx.cmd.split(' ')[0])
            child = parent.all_commands.get(ctx.cmd.split(' ')[1])

            if not child:
                return await ctx.send('Unknown subcommand.')

            paginator.add_line(prefixes[0] + ctx.cmd + ' ' + child.usage, empty=True)
            paginator.add_line(child.description)

            if child.aliases:
                aliases = ', '.join(child.aliases)

                paginator.add_line('')
                paginator.add_line(f'Aliases for this command are: {aliases}')

            for page in paginator.pages:
                await ctx.send(page)
                await asyncio.sleep(.333)

    async def on_ready(self):
        self.redis.set(
            '__info__',
            'This database is being used by the Amethyst Framework.')
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
        error = ('`{0}` in command `{1}`: ```py\n'
                 'Traceback (most recent call last):\n{2}{0}: {3}\n```')\
            .format(type(exception).__name__,
                    ctx.cmd, _traceback,
                    exception)

        await ctx.send(error)

    async def on_message(self, message):
        if (not message.content or
                message.author.bot or
                message.author.id in self.settings['blacklist']):
            return

        cleaned = message_parsing.parse_prefixes(message.content, prefixes)

        if (cleaned == message.content or
                cleaned[0] in string.whitespace):
            return

        cmd = message_parsing.get_cmd(cleaned)

        if not self.holder.get_command(cmd):
            return

        ctx = command_system.Context(message, self)

        try:
            await self.holder.run_command(ctx)
        except Exception as e:
            await self.handle_error(e, ctx)


amethyst = Amethyst(config, args, redis_conn)
amethyst.run(token)
