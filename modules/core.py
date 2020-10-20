import time
import traceback
from inspect import cleandoc
from textwrap import indent
from typing import TYPE_CHECKING

from discord.ext import commands

from utils import check

if TYPE_CHECKING:
    from notus import Notus


class Core(commands.Cog):
    def __init__(self, notus: Notus):
        self.notus = notus

        if "modules" not in self.settings:
            self.settings["modules"] = []

        if "eval" not in self.notus.db:
            self.notus.db["eval"] = {"env": {}, "count": 0}

        for module in self.settings["modules"]:
            if module not in self.notus.extensions:
                try:
                    self.notus.load_extension(module)
                except Exception as e:
                    self.settings["modules"].remove(module)

                    print(f"Extension `{module}` blew up.")
                    print("".join(traceback.format_tb(e.__traceback__)))

    @property
    def settings(self):
        return self.notus.db["settings"]

    @property
    def eval_data(self):
        return self.notus.db["eval"]

    @commands.group(aliases=["cog"], invoke_without_command=True)
    @check.owner()  # TODO: does this apply to whole group?
    async def module(self, ctx: commands.Context):
        """Module management"""
        await ctx.send_help(ctx.command)

    @module.command("load")
    async def module_load(self, ctx: commands.Context, *, module: str):
        module = "modules." + module.lower()

        if module not in self.notus.extensions:
            self.notus.load_extension(module)
            self.settings["modules"]

            await ctx.send("Module loaded.")
        else:
            await ctx.send(
                "That module is already loaded.\n"
                "Try using `module reload <name>` instead."
            )

    @module.command("unload")
    async def module_unload(self, ctx: commands.Context, *, module: str):
        module = "modules." + module.lower()

        if module in self.notus.extensions:
            self.notus.unload_extension(module)
            self.settings["modules"].removbe(module)

            await ctx.send("Module unloaded.")
        else:
            await ctx.send("That module is not currently loaded.")

    @module.command("reload")
    async def module_reload(self, ctx: commands.Context, *, module: str):
        module = "modules." + module.lower()

        if module in self.notus.extensions:
            self.notus.reload_extension(module)

            await ctx.send("Module reloaded.")
        else:
            await ctx.send(
                "That module isn't currently loaded.\n"
                "Try using `module load <name>` instead."
            )

    @commands.command()
    @check.instance_owner()
    async def arguments(self, ctx):
        """Lists all arguments."""
        await ctx.send(
            "Arguments for modules include: `load, unload & reload`.")

    @commands.command(aliases=['kys'])
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

    @commands.command(aliases=['debug'], usage='<code>')
    @check.instance_owner()
    async def eval(self, ctx):
        await ctx.send("This command is currently disabled.")
#        if self._eval.get('env') is None:
#            self._eval['env'] = {}
#        if self._eval.get('count') is None:
#            self._eval['count'] = 0
#
#        self._eval['env'].update({
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
