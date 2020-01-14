import json
import traceback
from typings import Set

import aiohttp
import discord.ext.commands as discord
from discord import utils as dutils

from utils.database import PlyvelDict

with open("config.json") as f:
    config = json.load(f)

token = config.get("NOTUS_TOKEN")
prefixes = config.get("NOTUS_PREFIXES", [])


class Notus(discord.Client):
    def __init__(self, config, **options):
        super().__init__(**options)
        self.db = PlyvelDict("./.notus_db")
        self.config = config
        # self.send_command_help = send_cmd_help

        if "settings" not in self.db:
            self.db["settings"] = {}

        if "blacklist" not in self.db["settings"]:
            self.db["settings"]["blacklist"] = []

    async def close(self):
        await self.session.close()
        await super().close()

    @property
    def owners(self) -> Set[int]:
        """Get owners of the bot, regardless if it's in a team or not."""
        return self.owner_ids or set([self.owner_id])

    async def on_ready(self):
        self.session = aiohttp.ClientSession()

        app = await self.application_info()
        self.invite_url = dutils.oauth_url(app.id)

        if app.team:
            self.owner_ids = set(app.team.members)
        else:
            self.owner_id = app.owner.id

        print("Ready.")
        print(self.invite_url)
        print(self.user.name)
        print("")

        print(f"Owners: {', '.join(self.owners)}")

        self.load_extension("modules.core")

    async def on_command_error(self, exception, context):
        # TODO: handle more exceptions
        if isinstance(exception, discord.MissingRequiredArgument):
            await self.send_command_help(context)
        elif isinstance(exception, discord.CommandInvokeError):
            exception = exception.original
            _traceback = traceback.format_tb(exception.__traceback__)
            _traceback = "".join(_traceback)
            error = (
                "`{0}` in command `{1}`: ```py\n"
                "Traceback (most recent call last):\n{2}{0}: {3}\n```"
            ).format(
                type(exception).__name__,
                context.command.qualified_name,
                _traceback,
                exception,
            )

            await context.send(error)
        elif isinstance(exception, discord.CommandNotFound):
            pass

    async def on_message(self, message):
        if (
            not message.content
            or message.author.bot
            or (
                str(message.author.id) in self.db["settings"]["blacklist"]
                and str(message.author.id) not in self.owners
            )
        ):
            return

        self.process_commands(message)


notus = Notus(config)
notus.run(token)
