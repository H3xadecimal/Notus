from discord.ext import commands
import discord


class Checks:
    def __init__(self, bot):
        self.xeili = xeili 

    def is_owner_check(ctx):
        ownerid = await self.get_owner_id()
        return ctx.message.author.id == ownerid


    def instance_owner():
        return commands.check(is_owner_check)

    async def get_owner_id(self):
        owner = await self.xeili.application_info()
        owner = str(owner.id)
        return owner
