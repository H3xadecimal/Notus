import textwrap
import time
import traceback
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

    # Eval code provided by Pandentia over at Thessia.
    # More of his work here: https://github.com/Pandentia
    @commands.command(aliases=["debug"])
    @check.instance_owner()
    async def eval(self, ctx: commands.Context, code: commands.Greedy[str]):
        """Run lots of code"""

        self.eval_data["env"].update({"ctx": ctx})

        # let's make this safe to work with
        code = ctx.suffix.replace("```py\n", "").replace("```", "").replace("`", "")
        to_eval = textwrap.dedent(
            f"""
            async def func(self):
              try:
                {textwrap.index(code, '    ')}
              finally:
                  if not cleared:
                    self.eval_data["env"].update(locals())
                  else:
                      cleared = False
        """
        ).strip()
        before = time.monotonic()

        cleared = False  # noqa: F841

        def clear():
            self.eval_data["env"] = {}
            self.eval_data["count"] = 0
            cleared = True  # noqa: F841

        try:
            exec(to_eval, self._eval["env"])  # noqa: S102

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

        # Handle a message thats too long for Discord
        if len(message) > 2000:
            message = "\n".join(message.split("\n")[1:-1])  # Remove codeblock

            async with self.notus.session.post(
                "https://hastebin.com/documents",
                data=message.encode(),
                headers={"Content-Type": "text/plain"},
            ) as resp:
                data = await resp.json()

            await ctx.send(
                f"Output too long, view online: https://hastebin.com/{data['key']}.py"
            )
        else:
            await ctx.send(message)


def setup(notus):
    notus.add_cog(Core())
