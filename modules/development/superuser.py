from utils.command_system import command
from utils import confirm
import discord


class SuperUser:
    def __init__(self, amethyst):
        self.amethyst = amethyst

    @command()
    @confirm.instance_owner()
    async def coreswap(self, ctx, *, path1, path2):
        """Command to swap your core module.

        Please note that this cog is in the devleopment folder,
        meaning that it should NOT be used in your bot until completion.
        It is far from complete and may contain a lot of bugs, Any bug report
        regarding any modules from the Development folder will be dismissed."""

        if not ctx.args:
            return await ctx.send('No arguments given.')

        try:
            self.amethyst.holder.unload_module(path1)
            self.amethyst.holder.load_module(path2)
            await ctx.send('Core swap complete.')
        except:
            await ctx.send('Core swap failed!.')


def setup(amethyst):
    return SuperUser(amethyst)
