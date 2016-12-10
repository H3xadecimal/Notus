import discord
from discord.ext import commands
import importlib
import inspect


class core:
    def __init__(self, xeili):
        self.xeili = xeili
        self.firmware = "Xeili Compact 0.0.2 (Original Firmware)"

    @commands.command(aliases=['cog', 'module'])
    async def fragment(self, name: str, argument: str=None):
        """Fragment management."""
        fragment_name = 'fragments.{0}'.format(name)
        argumentlist = ["--load", "--unload", "--reload", None]
        if argument == '--load' or None:
            if fragment_name not in list(self.xeili.extensions):
                plugin = importlib.import_module(fragment_name)
                importlib.reload(plugin)
                self.xeili.load_extension(plugin.__name__)
                await self.xeili.say('Input accepted, Fragment loaded.')
            else:
                await self.xeili.say('Ignoring Input, Fragment already loaded.')
        if argument == '--unload':
            if fragment_name in list(self.xeili.extensions):
                plugin = importlib.import_module(fragment_name)
                importlib.reload(plugin)
                self.xeili.unload_extension(plugin.__name__)
                await self.xeili.say('Input accepted, Fragment unloaded.')
            else:
                await self.xeili.say('Ignorning Input, Fragment not loaded or not found.')
        if argument == '--reload':
            if fragment_name in list(self.xeili.extensions):
                plugin = importlib.import_module(fragment_name)
                importlib.reload(plugin)
                self.xeili.unload_extension(plugin.__name__)
                self.xeili.load_extension(plugin.__name__)
                await self.xeili.say('Input accepted, Fragment reloaded.')
            else:
                await self.xeili.say('Ignoring Input, Specified fragment is not loaded.')
        if argument not in argumentlist:
            await self.xeili.say('Invalid argument, To see all arguments please do `[prefix]arguments`')

    @commands.command()
    async def arguments(self):
        """"Lists all arguments."""
        await self.xeili.say("Arguments for Fragments Include: `--load, --unload & --reload`.")

    @commands.command(pass_context=True, hidden=True, aliases=['debug'])
    async def eval(self, ctx, *, code: str):
        message = ctx.message
        author = ctx.message.author
        channel = ctx.message.channel
        server = ctx.message.server
        client = ctx.bot
        bot = ctx.bot

        if author.id == "yourid":
            output = eval(code)
            if inspect.isawaitable(output):
                output = await output

            await self.xeili.say('```py\n{0}\n```'.format(output))
        else:
            await self.xeili.say('You are not allowed to use this command... Suck it Pan!')


def setup(xeili):
    xeili.add_cog(core(xeili))