import utils.lookups as lookups
import discord
import inspect


class InvalidArg:
    def __init__(self, expected: str, example: str=None):
        self.expected = expected
        self.message = f'Invalid argument type. Expected `{self.expected}`.'

        if example:
            self.message += f'\n**Example:** `{example}`'

    def __bool__(self):
        return False

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.message


class Converters:
    def __init__(self, amethyst):
        self.amethyst = amethyst
        self.lookups = lookups.Lookups(amethyst)
        self.converter_map = {
            int: self.convert_to_int,
            float: self.convert_to_float,
            bool: self.convert_to_bool,
            discord.Member: self.convert_to_member,
            discord.User: self.convert_to_member,
            discord.TextChannel: self.convert_to_channel,
            discord.VoiceChannel: self.convert_to_voice_channel,
            discord.Role: self.convert_to_role
        }
        self.arg_complaints = {
            int: InvalidArg('integer', '10, 0, 400, -5'),
            float: InvalidArg('float', '0.5, 3.1415, -5.25'),
            bool: InvalidArg('boolean', 'yes, no, off, on'),
            discord.Member: InvalidArg('user', '@example, example, 1234567890 (id)'),
            discord.User: InvalidArg('user', '@example, example, 1234567890 (id)'),
            discord.TextChannel: InvalidArg('channel', '#example, example, 1234567890 (id)'),
            discord.VoiceChannel: InvalidArg('voice channel', '"Example Voice", 1234567890 (id)'),
            discord.Role: InvalidArg('role', '@example, example, 1234567890 (id)')
        }

    async def convert_arg(self, ctx, arg, type):
        """Converts an argument into the given type."""
        if type not in self.converter_map and type is not str:
            raise NotImplementedError()

        if type is str:
            return arg

        converter = self.converter_map[type]

        if len(inspect.getargspec(converter).args) == 2:
            return await converter(arg)
        else:
            return await converter(ctx, arg)

    async def convert_to_int(self, arg):
        try:
            return int(arg)
        except ValueError:
            return self.arg_complaints[int]

    async def convert_to_float(self, arg):
        try:
            return float(arg)
        except ValueError:
            return self.arg_complaints[float]

    async def convert_to_bool(self, arg):
        if arg.lower() in ('yes', 'y', 'true', 't', '1', 'enable', 'on', 'affirmative', '+'):
            return True
        elif arg.lower() in ('no', 'n', 'false', 'f', '0', 'disable', 'off', 'negative', '-'):
            return False
        else:
            return self.arg_complaints[bool]

    async def convert_to_member(self, ctx, arg):
        member = await self.lookups.member_lookup(ctx, arg, not_found_msg=False, suppress_error_msgs=True)

        if not member:
            return self.arg_complaints[discord.Member]
        else:
            return member

    async def convert_to_channel(self, ctx, arg):
        channel = await self.lookups.channel_lookup(ctx, arg, not_found_msg=False, suppress_error_msgs=True)

        if not channel:
            return self.arg_complaints[discord.TextChannel]
        else:
            return channel

    async def convert_to_voice_channel(self, ctx, arg):
        channel = await self.lookups.channel_lookup(ctx, arg, not_found_msg=False, suppress_error_msgs=True,
                                                    voice_only=True)

        if not channel:
            return self.arg_complaints[discord.VoiceChannel]
        else:
            return channel

    async def convert_to_role(self, ctx, arg):
        role = await self.lookups.role_lookup(ctx, arg, not_found_msg=False, suppress_error_msgs=True)

        if not role:
            return self.arg_complaints[discord.Role]
        else:
            return role
