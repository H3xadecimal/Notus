from utils.dusk import command
from utils import confirm
from utils.lookups import Lookups
import discord
import inspect
import traceback


class Core:
    def __init__(self, amethyst):
        self.amethyst = amethyst
        self.firmware = "Stock Firmware: Compact 0.3"
        self.settings = amethyst.data.load('settings')
        self.post_task = self.amethyst.loop.create_task(self.post())
        self.owners_task = amethyst.loop.create_task(self.owners_configuration())
        self.lookups = Lookups(amethyst)

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
                        print(''.join(traceback.format_tb(e.__traceback__)))

    async def owners_configuration(self):
        if 'owners' not in self.settings:
            self.settings['owners'] = []
        if self.amethyst.owner not in self.settings['owners']:
            self.settings['owners'].append(self.amethyst.owner)
        self.amethyst.owners = self.settings['owners']

    @command(aliases=['commands'], usage='[command]')
    async def help(self, ctx):
        """Show help for all the commands."""
        if not ctx.args:
            try:
                await self.amethyst.send_command_help(ctx)
            except discord.Forbidden:
                await ctx.send('Cannot send the help to you. Perhaps you have DMs blocked?')
        else:
            ctx.cmd = ctx.suffix
            await self.amethyst.send_command_help(ctx)

    @command(aliases=['cog'])
    @confirm.instance_owner()
    async def module(self, ctx, module: str, argument: str=None):
        """Module management."""

        argument_list = ["--load", "--unload", "--reload"]
        module_name = 'modules.' + module.lower()

        if argument == '--load' or argument is None:
            if module_name not in self.amethyst.holder.all_modules:
                self.amethyst.holder.load_module(module_name)
                self.settings['modules'].append(module_name)
                await ctx.send('Module loaded.')
            else:
                await ctx.send(
                    'The module you are trying to load is already loaded.\n'
                    'Please use the `--reload` argument instead.')
        elif argument == '--unload':
            if module_name in self.amethyst.holder.all_modules:
                self.amethyst.holder.unload_module(module_name)
                self.settings['modules'].remove(module_name)
                await ctx.send('Module unloaded.')
            else:
                await ctx.send(
                    'The module you are trying to unload '
                    'could not be found or is not loaded.')
        elif argument == '--reload':
            if module_name in self.amethyst.holder.all_modules:
                self.amethyst.holder.reload_module(module_name)
                await ctx.send('Module reloaded.')
            else:
                await ctx.send(
                        'The module you are trying to reload is not loaded.\n'
                        'Please try the `--load` argument.')
        elif argument not in argument_list:
            await ctx.send(
                    "The argument you specified is invalid.\n"
                    "Please check the available arguments using"
                    " `[prefix]arguments`.")

    @command()
    @confirm.instance_owner()
    async def arguments(self, ctx):
        """Lists all arguments."""
        await ctx.send(
            "Arguments for modules include: `--load, --unload & --reload`.")

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
