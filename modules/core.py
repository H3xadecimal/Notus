import discord
from discord.ext import commands
import importlib
import inspect
from utils import confirm
from utils.dataIO import dataIO


class core:
    def __init__(self, amethyst):
        self.amethyst = amethyst
        self.firmware = "Stock Firmware: Compact 0.3"
        self.settings = dataIO.load_json('settings')
        self.post_task = self.amethyst.loop.create_task(self.post())

    def __unload(self):
        self.post_task.cancel()

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
                await ctx.send('The module you are trying to load is already loaded.\n'
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
                        'The module you are trying to unload could not be found or is not loaded.')
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
                    "Please check the available arguments using `[prefix]arguments`.")

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
            "amethyst": self.amethyst,
        }

        output = eval(code, env)
        if inspect.isawaitable(output):
            output = await output

        await ctx.send('```py\n{0}\n```'.format(output))

    @commands.command(aliases=['kys'])
    @confirm.instance_owner()
    async def shutdown(self, ctx):
        """Shuts down the bot.... Duh."""
        await ctx.send("Logging out...")
        await self.amethyst.logout()


def setup(amethyst):
    amethyst.add_cog(core(amethyst))
