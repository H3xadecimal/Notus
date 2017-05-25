import discord
from discord.ext import commands
import importlib
import re
import textwrap
import inspect  # Don't remove this, it's used in eval
from utils import confirm
from utils.dataIO import dataIO


class core:
    def __init__(self, amethyst):
        self.amethyst = amethyst
        self.firmware = "Stock Firmware: Compact 0.3"
        self.settings = dataIO.load_json('settings')
        self.post_task = self.amethyst.loop.create_task(self.post())
        self.owners_task = amethyst.loop.create_task(
                self.owners_configuration())
        self.env = {}

    def __unload(self):
        self.post_task.cancel()
        self.owners_task.cancel()

    async def post(self):
        if 'modules' not in self.settings:
            self.settings['modules'] = []
        else:
            for module in self.settings['modules']:
                if module not in list(self.amethyst.extensions):
                    try:
                        self.amethyst.load_extension(module)
                    except:
                        self.settings['modules'].remove(module)
                        print("A module blew up... Idk which tho.")

    async def owners_configuration(self):
        if 'owners' not in self.settings:
            self.settings['owners'] = []
        if self.amethyst.owner not in self.settings['owners']:
            self.settings['owners'].append(self.amethyst.owner)
        self.amethyst.owners = self.settings['owners']

    @commands.command(aliases=['cog'])
    @confirm.instance_owner()
    async def module(self, ctx, name: str, argument: str):
        """Module management."""
        module_name = 'modules.{0}'.format(name)
        argumentlist = ["--load", "--unload", "--reload", None]
        if argument == '--load' or None:
            if module_name not in list(self.amethyst.extensions):
                plugin = importlib.import_module(module_name)
                importlib.reload(plugin)
                self.amethyst.load_extension(plugin.__name__)
                self.settings['modules'].append(module_name)
                await ctx.send('Module loaded.')
            else:
                await ctx.send(
                    'The module you are trying to load is already loaded.\n'
                    'Please use the `--reload` argument instead.')
        if argument == '--unload':
            if module_name in list(self.amethyst.extensions):
                plugin = importlib.import_module(module_name)
                importlib.reload(plugin)
                self.amethyst.unload_extension(plugin.__name__)
                self.settings['modules'].remove(module_name)
                await ctx.send('Module unloaded.')
            else:
                await ctx.send(
                    'The module you are trying to unload '
                    'could not be found or is not loaded.')
        if argument == '--reload':
            if module_name in list(self.amethyst.extensions):
                plugin = importlib.import_module(module_name)
                importlib.reload(plugin)
                self.amethyst.unload_extension(plugin.__name__)
                self.amethyst.load_extension(plugin.__name__)
                await ctx.send('Module reloaded.')
            else:
                await ctx.send(
                        'The module you are trying to reload is not loaded.\n'
                        'Please try the `--load` argument.')
        if argument not in argumentlist:
            await ctx.send(
                    "The argument you specified is invalid.\n"
                    "Please check the available arguments using"
                    " `[prefix]arguments`.")

    @commands.command()
    async def arguments(self, ctx):
        """Lists all arguments."""
        await ctx.send(
            "Arguments for Modules include: `--load, --unload & --reload`.")

    @commands.command(aliases=['debug'])
    @confirm.instance_owner()
    async def eval(self, ctx, *, code: str):
        env = {
            "message": ctx.message,
            "author": ctx.message.author,
            "channel": ctx.message.channel,
            "guild": ctx.message.guild,
            "ctx": ctx,
            "discord": discord,
            "self": self,
            "amethyst": self.amethyst,
            "inspect": inspect
        }

        self.env.update(env)

        code = code.strip("`")
        if code.startswith("py\n"):
            code = "\n".join(code.split("\n")[1:])
        if not re.search(
                "^(return|import|for|while|def|class|[a-zA-Z0-9]+\s*=)",
                code, re.M) and len(code.split("\n")) == 1:
            code = "_ = "+code

        # Ignore this shitcode, it works
        _code = "\n".join([
            "async def func(self, env):",
            "    locals().update(env)",
            "    old_locals = locals().copy()",
            "    try:",
            "{}",
            "        new_locals = {{k:v for k,v in locals().items() "
                "if k not in old_locals and k not in "
                "['old_locals','_','func']}}",
            "        if new_locals != {{}}:",
            "            return new_locals",
            "        else:",
            "            if inspect.isawaitable(_):",
            "                _ = await _",
            "            return _",
            "    finally:",
            "        self.env.update({{k:v for k,v in locals().items() "
                "if k not in old_locals and k not in "
                "['old_locals','_','new_locals','func']}})"
        ]).format(textwrap.indent(code, '        '))

        exec(_code, self.env)
        func = self.env['func']
        res = await func(self, self.env)
        if res is not None:
            self.env["_"] = res
            await ctx.send('```py\n{0}\n```'.format(res))
        else:
            await ctx.send("\N{THUMBS UP SIGN}")

    @commands.command(aliases=['kys'])
    @confirm.instance_owner()
    async def shutdown(self, ctx):
        """Shuts down the bot.... Duh."""
        await ctx.send("Logging out...")
        await self.amethyst.logout()


def setup(amethyst):
    amethyst.add_cog(core(amethyst))
