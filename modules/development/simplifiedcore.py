import discord
import inspect
from utils.command_system import command
from utils import confirm
from utils.dataIO import dataIO
from utils.lookups import Lookups


class Core:
    def __init__(self, amethyst):
        self.amethyst = amethyst
        self.db = amethyst.db
        self.firmware = "Simplified 0.1"
        self.post_task = self.amethyst.loop.create_task(self.post())
        self.owners_task = amethyst.loop.create_task(self.owners_configuration())
        self.lookups = Lookups(amethyst)

    @property
    def settings(self):
        return self.db['settings']

    def __unload(self):
        self.post_task.cancel()
        self.owners_task.cancel()

    async def post(self):
        if 'modules' not in self.settings:
            self.settings['modules'] = []
        else:
            for module in self.settings['modules']:
                if module not in self.amethyst.holder.all_modules:
                    try:
                        self.amethyst.holder.load_module(module)
                    except Exception as e:
                        self.settings['modules'].remove(module)
                        print(f"Module `{module}` blew up.")
                        print(e)

    async def owners_configuration(self):
        if 'owners' not in self.settings:
            self.settings['owners'] = []
        if self.amethyst.owner not in self.settings['owners']:
            self.settings['owners'].append(self.amethyst.owner)
        self.amethyst.owners = self.settings['owners']

    @command(aliases=['-l'], usage='<module>')
    @confirm.instance_owner()
    async def load(self, ctx):
        """Loads a module."""
        if not ctx.args:
            return await ctx.send('Please specify a module to load.')

        module_name = 'modules.' + ctx.args[0].lower()

        if module_name not in self.amethyst.holder.all_modules:
            self.amethyst.holder.load_module(module_name)
            self.settings['modules'].append(module_name)
            await ctx.send('Module loaded.')
        else:
            msg = await ctx.send('Module already loaded, Reloading...')
            self.amethyst.holder.reload_module(module_name)
            await msg.edit(content='Module reloaded.')

    @command(aliases=['-u'], usage='<module>')
    @confirm.instance_owner()
    async def unload(self, ctx):
        """Unloads a module."""
        if not ctx.args:
            return await ctx.send('Please specify a module to unload.')

        module_name = 'modules.' + ctx.args[0].lower()

        if module_name in self.amethyst.holder.all_modules:
            self.amethyst.holder.unload_module(module_name)
            self.settings['modules'].remove(module_name)
            await ctx.send('Module unloaded.')
        else:
            await ctx.send('Module is not loaded.')

    @command(aliases=['-r'], usage='<module>')
    @confirm.instance_owner()
    async def reload(self, ctx):
        """Reloads a module."""
        if not ctx.args:
            return await ctx.send('Please specify a module to reload.')

        module_name = 'modules.' + ctx.args[0].lower()

        if module_name in self.amethyst.holder.all_modules:
            self.amethyst.holder.reload_module(module_name)
            await ctx.send('Module reloaded.')
        else:
            await ctx.send('Module not loaded.')

    @command(aliases=['debug'], usage='<code>')
    @confirm.instance_owner()
    async def eval(self, ctx):
        env = {
            "message": ctx.msg,
            "author": ctx.msg.author,
            "channel": ctx.msg.channel,
            "guild": ctx.msg.guild,
            "ctx": ctx,
            "discord": discord,
            "lookups": self.lookups,
            "self": self.amethyst,
        }

        output = eval(ctx.suffix, env)
        if inspect.isawaitable(output):
            output = await output

        await ctx.send('```py\n{0}\n```'.format(output))

    @command(aliases=['kys'])
    @confirm.instance_owner()
    async def shutdown(self, ctx):
        """Shuts down the bot.... Duh."""
        await ctx.send("Logging out...")
        await self.amethyst.logout()


def setup(amethyst):
    return Core(amethyst)
