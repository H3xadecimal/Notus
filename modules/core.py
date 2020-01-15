import textwrap
import time
import traceback
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import check

if TYPE_CHECKING:
    from notus import Notus


class Core(commands.Cog):
    def __init__(self, notus: Notus):
        self.notus = notus
        self._eval = {}

        self.post_load()

    @property
    def settings(self):
        return self.notus.db["settings"]

    def post_load(self):
        if "modules" not in self.settings:
            self.settings["modules"] = []

        for module in self.settings["modules"]:
            if module not in self.notus.extensions:
                try:
                    self.notus.load_extension(module)
                except Exception as e:
                    self.settings["modules"].remove(module)

                    print(f"Extension `{module}` blew up.")
                    print("".join(traceback.format_tb(e.__traceback__)))

    @commands.group(aliases=["cog"])
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

    @commands.command(aliases=["kys"])
    @check.owner()
    async def shutdown(self, ctx: commands.Context):
        """Shuts down the bot... duh"""
        await ctx.send("Cya")
        await self.notus.logout()

    # Now this piece of shit code is partially broken.
    # Large output evals used to upload to pastebin but their API is now private.
    # Instead large output evals are not printed at all thus causing a problem when debugging.
    # Temporarily disabled until fixed.
    # Also leaving that one to @Ovyerus because my last 6 attempts at fixing it failed.

    @commands.command(aliases=["debug"])
    @check.instance_owner()
    async def eval(self, ctx: commands.Context, code: commands.Greedy[str]):
        if self._eval.get("env") is None:
            self._eval["env"] = {}
        if self._eval.get("count") is None:
            self._eval["count"] = 0

        self._eval["env"].update(
            {
                "ctx": ctx,
                "message": ctx.message,
                "channel": ctx.message.channel,
                "guild": ctx.message.guild,
                "server": ctx.message.guild,
                "author": ctx.message.author,
            }
        )

        # let's make this safe to work with
        code = ctx.suffix.replace("```py\n", "").replace("```", "").replace("`", "")
        to_eval = textwrap.dedent(
            f"""
            async def func(self):
              try:
                {textwrap.index(code, '    ')}
              finally:
                self._eval['env'].update(locals())
        """
        ).strip()
        before = time.monotonic()

        try:
            exec(to_eval, self._eval["env"])

            func = self._eval["env"]["func"]
            output = await func(self)

            if output is not None:
                output = repr(output)
        except Exception as e:
            output = f"{type(e).__name__}: {e}"

        after = time.monotonic()
        self._eval["count"] += 1
        count = self._eval["count"]
        code = code.split("\n")

        if len(code) == 1:
            in_ = f"In [{count}]: {code[0]}"
        else:
            first = code[0]
            rest = code[1:]
            rest = "\n".join(rest)
            count_len = len(str(count)) + 2
            rest = textwrap.indent(textwrap.indent(rest, "...: "), " " * count_len)

            in_ = f"In [{count}]: {first}\n{rest}"

        message = f"```py\n{in_}"
        ms = round((after - before) * 1000)

        if output is not None:
            message += f"\nOut[{count}]: {output}"

        if ms > 100:  # noticeable delay
            message += f"\n# {ms} ms\n```".format(ms)
        else:
            message += "\n```"

        try:
            if ctx.msg.author.id == self.notus.user.id:
                await ctx.msg.edit(content=message)
            else:
                await ctx.send(message)
        except discord.HTTPException:
            await ctx.msg.channel.trigger_typing()
            await ctx.send("Output was too big to be printed.")


# Eval code provided by Pandentia over at Thessia.
# More of his work here: https://github.com/Pandentia


def setup(notus):
    notus.add_cog(Core())
