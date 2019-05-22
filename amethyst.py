from discord import utils as dutils
from discord.ext.commands import Paginator
from utils import dusk, message_parsing
from utils.database import PlyvelDict
import utils.arg_converters as arg_converters
import traceback
import argparse
import json
import discord
import string
import asyncio
import aiohttp

with open("config.json") as f:
    config = json.load(f)

token = config.get('AMETHYST_TOKEN')
prefixes = config.get('AMETHYST_PREFIXES', [])
tagline = config.get('AMETHYST_TAGLINE', '{} is an instance of Amethyst, learn more about the project at '
                     'https://github.com/awau/Amethyst')


class Amethyst(discord.Client):
    def __init__(self, config, **options):
        super().__init__(**options)
        self.db = PlyvelDict('./.notus_db')
        self.owner = None
        self.config = config
        self.holder = dusk.CommandHolder(self)
        self.commands = self.holder
        self.converters = arg_converters.Converters(self)
        self.send_cmd_help = self.holder.send_cmd_help
        self.send_command_help = self.send_cmd_help
        self.tagline = tagline

        if 'settings' not in self.db:
            self.db['settings'] = {}

        if 'blacklist' not in self.db['settings']:
            self.db['settings']['blacklist'] = []

    async def on_ready(self):
        self.session = aiohttp.ClientSession()

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

    async def close(self):
        await self.session.close()
        await super().close()

    async def on_message(self, message):
        if (not message.content or message.author.bot or
                (str(message.author.id) in self.db['settings']['blacklist'] and
                 str(message.author.id) not in self.owners)
        ):
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


amethyst = Amethyst(config)
amethyst.run(token)
