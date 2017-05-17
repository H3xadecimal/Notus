import discord
import asyncio


class BadResponseException(Exception):
    pass


class Lookups:
    def __init__(self, amethyst):
        self.amethyst = amethyst

    async def __prompt__(self, ctx, what, what_list, type):
        if type == 'members':
            what_list = [(x.name, x.discriminator, x.id) for x in what_list][:10]
            format_list = ['{0}. {1[0]}#{1[1]}'.format(what_list.index(x) + 1, x) for x in what_list]
            msg = '''```py
>>> Multiple users found matching '{0}'.
>>> Select the wanted user by typing their corresponding number.
>>> If you cannot find the user you want, try refining your search.

{1}
```'''.format(what, '\n'.join(format_list))

            delet = await ctx.send(msg)
            try:
                msg = await self.amethyst.wait_for('message',
                                                   check=lambda m: m.author.id == ctx.message.author.id,
                                                   timeout=15)
                choice = int(msg.content)

                if choice == 0 or choice > len(format_list):
                    await ctx.send('Choice index out of range (0 or larger than {}).'.format(len(format_list) + 1))
                    return BadResponseException()
                elif isinstance(ctx.message.channel, discord.DMChannel):
                    choice = [u for u in self.amethyst.users if u.id == what_list[choice - 1][2]][0]
                else:
                    choice = [m for m in ctx.guild.members if m.id == what_list[choice - 1][2]][0]

                await delet.delete()
                return choice
            except asyncio.TimeoutError:
                await ctx.send('Choice timed out.')
                return BadResponseException()
            except ValueError:
                await ctx.send('Invalid choice (Full number required).')
                return BadResponseException()
        elif type == 'channels':
            what_list = [(x.name, x.id) for x in what_list][:10]
            format_list = ['{0}. {1}'.format(what_list.index(x) + 1, x[0]) for x in what_list]
            msg = '''```py
>>> Multiple channels found matching '{0}'.
>>> Select the wanted channel by typing its corresponding number.
>>> If you cannot find the channel you want, try refining your search.

{1}
```'''.format(what, '\n'.join(format_list))

            delet = await ctx.send(msg)
            try:
                msg = await self.amethyst.wait_for('message',
                                                   check=lambda m: m.author.id == ctx.message.author.id,
                                                   timeout=15)
                choice = int(msg.content)

                if choice == 0 or choice > len(format_list):
                    await ctx.send('Choice index out of range (0 or larger than {}).'.format(len(format_list) + 1))
                    return BadResponseException()
                else:
                    choice = [c for c in ctx.guild.channels if c.id == what_list[choice - 1][1]][0]

                await delet.delete()
                return choice
            except asyncio.TimeoutError:
                await ctx.send('Choice timed out.')
                return BadResponseException()
            except ValueError:
                await ctx.send('Invalid choice (Full number required).')
                return BadResponseException()
        elif type == 'guilds':
            what_list = [(x.name, x.id) for x in what_list][:10]
            format_list = ['{0}. {1}'.format(what_list.index(x) + 1, x[0]) for x in what_list]
            msg = '''```py
>>> Multiple servers found matching '{0}'.
>>> Select the wanted server by typing its corresponding number.
>>> If you cannot find the server you want, try refining your search.

{1}
```'''.format(what, '\n'.join(format_list))

            delet = await ctx.send(msg)
            try:
                msg = await self.amethyst.wait_for('message',
                                                   check=lambda m: m.author.id == ctx.message.author.id,
                                                   timeout=15)
                choice = int(msg.content)

                if choice == 0 or choice > len(format_list):
                    await ctx.send('Choice index out of range (0 or larger than {}).'.format(len(format_list) + 1))
                    return BadResponseException()
                else:
                    choice = [g for g in self.amethyst.guilds if g.id == what_list[choice - 1][1]][0]

                await delet.delete()
                return choice
            except asyncio.TimeoutError:
                await ctx.send('Choice timed out.')
                return BadResponseException()
            except ValueError:
                await ctx.send('Invalid choice (Full number required).')
                return BadResponseException()
        elif type == 'roles':
            what_list = [(x.name, x.id) for x in what_list]
            format_list = ['{0}. {1}'.format(what_list.index(x) + 1, x[0]) for x in what_list][:10]
            msg = '''```py
>>> Multiple roles found matching '{0}'.
>>> Select the wanted role by typing its corresponding number.
>>> If you cannot find the role you want, try refining your search.

{1}
```'''.format(what, '\n'.join(format_list))

            delet = await ctx.send(msg)
            try:
                msg = await self.amethyst.wait_for('message',
                                                   check=lambda m: m.author.id == ctx.message.author.id,
                                                   timeout=15)
                choice = int(msg.content)

                if choice == 0 or choice > len(format_list):
                    await ctx.send('Choice index out of range (0 or larger than {}).'.format(len(format_list) + 1))
                    return BadResponseException()
                else:
                    choice = [r for r in ctx.guild.roles if r.id == what_list[choice - 1][1]][0]

                await delet.delete()
                return choice
            except asyncio.TimeoutError:
                await ctx.send('Choice timed out.')
                return BadResponseException()
            except ValueError:
                await ctx.send('Invalid choice (Full number required).')
                return BadResponseException()
        else:
            raise TypeError('Invalid type {0}'.format(type))

    async def member_lookup(self, ctx, who, not_found_msg=True):
        member = None

        if len(ctx.message.mentions) > 0:
            member = ctx.message.mentions[0]
        else:
            if isinstance(ctx.message.channel, discord.DMChannel):
                members = [u for u in self.amethyst.users if who.lower() in u.name.lower()]

                if len(members) > 1:
                    member = await self.__prompt__(ctx, who, members, 'members')
                elif len(members) == 1:
                    member = members[0]
                else:
                    if not_found_msg:
                        await ctx.send('User not found.')
                        member = BadResponseException()

                return member
            else:
                members = [m for m in ctx.guild.members if who.lower() in m.name.lower() or
                           (m.nick and who.lower() in m.nick.lower())]

                if len(members) > 1:
                    member = await self.__prompt__(ctx, who, members, 'members')
                elif len(members) == 1:
                    member = members[0]
                else:
                    if not_found_msg:
                        await ctx.send('User not found.')
                        member = BadResponseException()

                return member

    async def channel_lookup(self, ctx, what, not_found_msg=True):
        if isinstance(ctx.message.channel, discord.DMChannel):
            await ctx.send('Channels cannot be looked up in DMs.')
            return BadResponseException()
        else:
            channel = None
            channels = [c for c in ctx.guild.channels if what.lower() in c.name.lower()]

            if len(channels) > 1:
                channel = await self.__prompt__(ctx, what, channels, 'channels')
            elif len(channels) == 1:
                channel = channels[0]
            else:
                if not_found_msg:
                    await ctx.send('Channel not found.')
                    channel = BadResponseException()

            return channel

    async def role_lookup(self, ctx, what, not_found_msg=True):
        if isinstance(ctx.message.channel, discord.DMChannel):
            await ctx.send('Roles cannot be looked up in DMs.')
            return BadResponseException()
        else:
            role = None
            roles = [r for r in ctx.guild.roles if what.lower() in r.name.lower()]

            if len(roles) > 1:
                role = await self.__prompt__(ctx, what, roles, 'roles')
            elif len(roles) == 1:
                role = roles[0]
            else:
                if not_found_msg:
                    await ctx.send('Role not found.')
                    role = BadResponseException()

            return role

    async def guild_lookup(self, ctx, what, not_found_msg=True):
        guild = None
        guilds = [g for g in self.amethyst.guilds if what.lower() in g.name.lower()]

        if len(guilds) > 1:
            guild = await self.__prompt__(ctx, what, guilds, 'guilds')
        elif len(guilds) == 1:
            guild = guilds[0]
        else:
            if not_found_msg:
                await ctx.send('Server not found.')
                guild = BadResponseException()

        return guild
