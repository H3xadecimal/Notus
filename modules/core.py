import textwrap
import time
import traceback

import discord
from discord.ext import commands

from utils import check


class Core:
    def __init__(self, notus):
        self.notus = notus
        self.db = notus.db
        self._eval = {}

        self.post_load()

    @property
    def settings(self):
        return self.db["settings"]

    def post_load(self):
        if "modules" not in self.settings:
            self.settings["modules"] = []

        for module in self.settings["modules"]:
            if module not in list(self.notus.extensions):
                try:
                    self.notus.load_extension(module)
                except Exception as e:
                    self.settings["modules"].remove(module)

                    print(f"Module `{module}` blew up.")
                    print("".join(traceback.format_tb(e.__traceback__)))

        if "owners" not in self.settings:
            self.settings["owners"] = []

        if self.notus.owner not in self.settings["owners"]:
            self.settings["owners"].append(self.notus.owner)

        self.notus.owners = self.settings["owners"]

    @commands.command()
    async def help(self, ctx):
        """Show help for all the commands."""
        if not ctx.args:
            try:
                await self.notus.send_command_help(ctx)
            except discord.Forbidden:
                await ctx.send(
                    "Cannot send the help to you. Perhaps you have DMs blocked?"
                )
        else:
            ctx.cmd = ctx.suffix
            await self.notus.send_command_help(ctx)

    # At the time of rewriting this, I am unaware if importlib is still required to load/unload/reload
    # modules on the latest version of discord.py as the rewrite was in beta during this code and is now on release version.
    # CC @Ovyerus to test.

    @commands.command(aliases=["cog"])
    @check.instance_owner()
    async def module(self, ctx, *, argument: str = None, module: str):
        """Module management."""

        argument_list = ["load", "unload", "reload"]
        module_name = "modules." + module.lower()

        if argument == "load" or argument is None:
            if module_name not in list(self.notus.extensions):
                self.notus.load_extension(module_name)
                self.settings["modules"].append(module_name)
                await ctx.send("Module loaded.")
            else:
                await ctx.send(
                    "The module you are trying to load is already loaded.\n"
                    "Please use the `reload` argument instead."
                )
        elif argument == "unload":
            if module_name in list(self.notus.extensions):
                self.notus.unload_extension(module_name)
                self.settings["modules"].remove(module_name)
                await ctx.send("Module unloaded.")
            else:
                await ctx.send(
                    "The module you are trying to unload "
                    "could not be found or is not loaded."
                )
        elif argument == "--reload":
            if module_name in list(self.notus.extensions):
                self.notus.reload_extension(module_name)
                await ctx.send("Module reloaded.")
            else:
                await ctx.send(
                    "The module you are trying to reload is not loaded.\n"
                    "Please try the `load` argument."
                )
        elif argument not in argument_list:
            await ctx.send(
                "The argument you specified is invalid.\n"
                "Please check the available arguments using"
                " `[prefix]arguments`."
            )

    @command()
    @check.instance_owner()
    async def arguments(self, ctx):
        """Lists all arguments."""
        await ctx.send("Arguments for modules include: `load, unload & reload`.")

    @command(aliases=["kys"])
    @check.instance_owner()
    async def shutdown(self, ctx):
        """Shuts down the bot.... Duh."""
        await ctx.send("Logging out...")
        await self.notus.logout()

    # Now this piece of shit code is partially broken.
    # Large output evals used to upload to pastebin but their API is now private.
    # Instead large output evals are not printed at all thus causing a problem when debugging.
    # Temporarily disabled until fixed.
    # Also leaving that one to @Ovyerus because my last 6 attempts at fixing it failed.

    @command(aliases=["debug"], usage="<code>")
    @check.instance_owner()
    async def eval(self, ctx):
        await ctx.send("This command is currently disabled.")


#        if self._eval.get('env') is None:
#            self._eval['env'] = {}
#        if self._eval.get('count') is None:
#            self._eval['count'] = 0
#
#        self._eval['env'].update({
#            'lookups': self.lookups,
#            'ctx': ctx,
#            'message': ctx.msg,
#            'channel': ctx.msg.channel,
#            'guild': ctx.msg.guild,
#            'server': ctx.msg.guild,
#            'author': ctx.msg.author
#        })
#
# let's make this safe to work with
#        code = ctx.suffix.replace('```py\n', '').replace('```', '').replace('`', '')
#        _code = "async def func(self):\n  try:\n{}\n  finally:\n    self._eval['env'].update(locals())"\
#                .format(textwrap.indent(code, '    '))
#        before = time.monotonic()
#
# noinspection PyBroadException
#        try:
#            exec(_code, self._eval['env'])
#
#            func = self._eval['env']['func']
#            output = await func(self)
#
#            if output is not None:
#                output = repr(output)
#        except Exception as e:
#            output = '{}: {}'.format(type(e).__name__, e)
#
#        after = time.monotonic()
#        self._eval['count'] += 1
#        count = self._eval['count']
#        code = code.split('\n')
#
#        if len(code) == 1:
#            _in = 'In [{}]: {}'.format(count, code[0])
#        else:
#            _first_line = code[0]
#            _rest = code[1:]
#            _rest = '\n'.join(_rest)
#            _countlen = len(str(count)) + 2
#            _rest = textwrap.indent(_rest, '...: ')
#            _rest = textwrap.indent(_rest, ' ' * _countlen)
#            _in = 'In [{}]: {}\n{}'.format(count, _first_line, _rest)
#
#        message = '```py\n{}'.format(_in)
#        ms = int(round((after - before) * 1000))
#
#        if output is not None:
#            message += '\nOut[{}]: {}'.format(count, output)
#
#        if ms > 100:  # noticeable delay
#            message += '\n# {} ms\n```'.format(ms)
#        else:
#            message += '\n```'
#
#        try:
#            if ctx.msg.author.id == self.notus.user.id:
#                await ctx.msg.edit(content=message)
#            else:
#                await ctx.send(message)
#        except discord.HTTPException:
#            await ctx.msg.channel.trigger_typing()
#            await ctx.send('Output was too big to be printed.')

# Eval code provided by Pandentia over at Thessia.
# More of his work here: https://github.com/Pandentia

# Sidenote, uncommenting all of this is gonna be fun, goodluck Ovy.


def setup(notus):
    notus.add_cog(Core())
