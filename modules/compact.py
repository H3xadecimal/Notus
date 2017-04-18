import discord
from discord.ext import commands
import importlib
import inspect
from utils import confirm
from utils.dataIO import dataIO


class core:
    def __init__(self, xeili):
        self.xeili = xeili
        self.firmware = "Xeili Compact 0.0.2 (Original Firmware)"
        self.settings = dataIO.load_json('settings')
        self.post_task = self.xeili.loop.create_task(self.post())

    def __unload(self):
        self.post_task.cancel()

    async def post(self):
        if 'modules' not in self.settings:
            self.settings['modules'] = []
        else:
            for module in self.settings['modules']:
                if module not in list(self.xeili.extensions):
                    try:
                        self.xeili.load_extension(module)
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
            if module_name not in list(self.xeili.extensions):
                plugin = importlib.import_module(module_name)
                importlib.reload(plugin)
                self.xeili.load_extension(plugin.__name__)
                self.settings['modules'].append(module_name)
                await ctx.send('Input accepted, Module loaded.')
            else:
                await ctx.send('Ignoring Input, Module already loaded.')
        if argument == '--unload':
            if module_name in list(self.xeili.extensions):
                plugin = importlib.import_module(module_name)
                importlib.reload(plugin)
                self.xeili.unload_extension(plugin.__name__)
                self.settings['modules'].remove(module_name)
                await ctx.send('Input accepted, Module unloaded.')
            else:
                await ctx.send('Ignoring Input, Module not loaded or not found.')
        if argument == '--reload':
            if module_name in list(self.xeili.extensions):
                plugin = importlib.import_module(module_name)
                importlib.reload(plugin)
                self.xeili.unload_extension(plugin.__name__)
                self.xeili.load_extension(plugin.__name__)
                await ctx.send('Input accepted, Module reloaded.')
            else:
                await ctx.send('Ignoring Input, Specified Module is not loaded.')
        if argument not in argumentlist:
            await ctx.send('Invalid argument, To see all arguments please do `xei arguments`')

    @commands.command()
    async def arguments(self, ctx):
        """Lists all arguments."""
        await ctx.send("Arguments for Fragments Include: `--load, --unload & --reload`.")

    @commands.command(aliases=['debug'])
    @confirm.instance_owner()
    async def eval(self, ctx, *, code: str):
        message = ctx.message
        author = ctx.message.author
        channel = ctx.message.channel
        guild = ctx.message.guild
        ctx = ctx
        bot = self.xeili
        client = self.xeili

        output = eval(code)
        if inspect.isawaitable(output):
            output = await output
        else:
            pass

        await ctx.send('```py\n{0}\n```'.format(output))

    @commands.command(aliases=['kys'])
    @confirm.instance_owner()
    async def shutdown(self, ctx):
        """Shuts down the bot.... Duh."""
        await ctx.send("Logging out...")
        await self.xeili.logout()

def setup(xeili):
    xeili.add_cog(core(xeili))