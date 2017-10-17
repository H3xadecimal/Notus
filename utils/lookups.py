import asyncio
import re
import discord


class BadResponseException(Exception):
    def __bool__(self):
        return False


class Lookups:
    def __init__(self, amethyst):
        self.amethyst = amethyst

    async def __prompt__(self, ctx, what, what_list, type, *, suppress_error_msgs=False):
        if type == 'members':
            what_list = [(x.name, x.discriminator, x.id) for x in what_list][:10]
            format_list = ['{0}. {1[0]}#{1[1]}'.format(what_list.index(x) + 1, x) for x in what_list]
        elif type in ['channels', 'roles', 'guilds']:
            what_list = [(x.name, x.id) for x in what_list][:10]
            format_list = ['{}. {}'.format(what_list.index(x) + 1, x[0]) for x in what_list]
        else:
            raise TypeError('Unknown type `{}`'.format(type))

        msg = '''```py
>>> Multiple {0} found matching '{1}'.
>>> Select the wanted {2} by typing their corresponding number.
>>> If you cannot find the {2} you want, try refining your search.

{3}
```'''.format(type.capitalize(), what, type[:-1], '\n'.join(format_list))

        delet = await ctx.send(msg)
        try:
            msg = await self.amethyst.wait_for('message',
                                               check=lambda m: m.author.id == ctx.msg.author.id,
                                               timeout=15)
            choice = int(msg.content)

            if choice < 0 or choice > len(format_list):
                if not suppress_error_msgs:
                    await ctx.send('Choice is either too large or too small.')
                return BadResponseException()

            if type == 'members':
                if ctx.is_dm():
                    choice = [u for u in self.amethyst.get_all_members() if u.id == what_list[choice - 1][2]][0]
                else:
                    choice = [m for m in ctx.msg.guild.members if m.id == what_list[choice - 1][2]][0]
            elif type == 'channels':
                choice = [c for c in ctx.msg.guild.channels if c.id == what_list[choice - 1][1]][0]
            elif type == 'guilds':
                choice = [g for g in self.amethyst.guilds if g.id == what_list[choice - 1][1]][0]
            elif type == 'roles':
                choice = [r for r in ctx.msg.guild.roles if r.id == what_list[choice - 1][1]][0]
            else:
                raise TypeError('Unknown type `{}`'.format(type))

            await delet.delete()
            return choice
        except asyncio.TimeoutError:
            await delet.delete()

            if not suppress_error_msgs:
                await ctx.send('Choice timed out.')

            return BadResponseException()
        except ValueError:
            await delet.delete()

            if not suppress_error_msgs:
                await ctx.send('Invalid choice (Full number required).')

            return BadResponseException()

    async def member_lookup(self, ctx, who, *, not_found_msg=True, suppress_error_msgs=False):
        member = None

        if re.match(r'<@!?\d+>', who):
            id = int(re.match(r'<@!?(\d+)>', who)[1])

            if ctx.is_dm():
                member = [m for m in self.amethyst.get_all_members() if m.id == id]

                if member:
                    return member[0]
                else:
                    return None
            else:
                member = [m for m in ctx.msg.guild.members if m.id == id]

                if member:
                    return member[0]
                else:
                    return None
        else:
            if ctx.is_dm():
                if re.match(r'^\d+$', who) and len(who) != 4:
                    members = [u for u in self.amethyst.get_all_members() if who in str(u.id) or who in u.name]
                elif re.match(r'^\d+$', who) and len(who) == 4:
                    members = [u for u in self.amethyst.get_all_members() if who == u.discriminator]
                else:
                    members = [u for u in self.amethyst.get_all_members() if who.lower() in u.name.lower()]

                if len(members) > 1:
                    member = await self.__prompt__(ctx, who, members,
                                                   'members', suppress_error_msgs=suppress_error_msgs)
                elif len(members) == 1:
                    member = members[0]
                else:
                    if not_found_msg:
                        await ctx.send('User not found.')
                        member = BadResponseException()

                return member
            else:
                if re.match(r'^\d+$', who) and len(who) != 4:
                    members = [m for m in ctx.msg.guild.members if who in str(m.id) or who in m.name]
                elif re.match(r'^\d+$', who) and len(who) == 4:
                    members = [m for m in ctx.msg.guild.members if who == m.discriminator]
                else:
                    members = [m for m in ctx.msg.guild.members if who.lower() in m.name.lower() or
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

    async def channel_lookup(self, ctx, what, *, not_found_msg=True, suppress_error_msgs=False, voice_only=False):
        if ctx.is_dm():
            await ctx.send('Channels cannot be looked up in DMs.')
            return BadResponseException()

        channel = None

        if re.match(r'<@!?\d+>', what):
            id = int(re.match(r'<@!?(\d+)>', what)[1])
            channel = [c for c in ctx.msg.guild.channels if c.id == id]

            if channel:
                return channel[0]
            else:
                return None

        if voice_only:
            channels = [c for c in ctx.msg.guild.channels if (what.lower() in c.name.lower() or what in str(c.id)) and
                        isinstance(c, discord.VoiceChannel)]
        else:
            channels = [c for c in ctx.msg.guild.channels if what.lower() in c.name.lower() or what in str(c.id)]

        if len(channels) > 1:
            channel = await self.__prompt__(ctx, what, channels, 'channels', suppress_error_msgs=suppress_error_msgs)
        elif len(channels) == 1:
            channel = channels[0]
        else:
            if not_found_msg:
                await ctx.send('Channel not found.')
                channel = BadResponseException()

        return channel

    async def role_lookup(self, ctx, what, *, not_found_msg=True, suppress_error_msgs=False):
        if ctx.is_dm():
            await ctx.send('Roles cannot be looked up in DMs.')
            return BadResponseException()
        else:
            role = None
            roles = [r for r in ctx.msg.guild.roles if what.lower() in r.name.lower()]

            if len(roles) > 1:
                role = await self.__prompt__(ctx, what, roles, 'roles', suppress_error_msgs=suppress_error_msgs)
            elif len(roles) == 1:
                role = roles[0]
            else:
                if not_found_msg:
                    await ctx.send('Role not found.')
                    role = BadResponseException()

            return role

    async def guild_lookup(self, ctx, what, *, not_found_msg=True, suppress_error_msgs=False):
        guild = None
        guilds = [g for g in self.amethyst.guilds if what.lower() in g.name.lower()]

        if len(guilds) > 1:
            guild = await self.__prompt__(ctx, what, guilds, 'guilds', suppress_error_msgs=suppress_error_msgs)
        elif len(guilds) == 1:
            guild = guilds[0]
        else:
            if not_found_msg:
                await ctx.send('Server not found.')
                guild = BadResponseException()

        return guild
