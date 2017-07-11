from typing import Callable, List, Union, Set
from utils import message_parsing
import discord
import inspect
import re
import sys
import asyncio

PRETTY_PRINTED_PERMS = {
    'create_insant_invite': 'Create Instant Invite',
    'kick_members': 'Kick Members',
    'ban_members': 'Ban Members',
    'administrator': 'Administrator',
    'manage_channels': 'Manage Channels',
    'manage_guild': 'Manage Server',
    'add_reactions': 'Add Reactions',
    'read_messages': 'Read Messages',
    'send_messages': 'Send Messages',
    'send_tts_messages': 'Send TTS Messages',
    'manage_messages': 'Manage Messages',
    'embed_links': 'Embed Links',
    'attach_files': 'Attach Files',
    'read_message_history': 'Read Message History',
    'mention_everyone': 'Mention Everyone',
    'external_emojis': 'Use External Emojis',
    'connect': 'Connect',
    'speak': 'Speak',
    'mute_embers': 'Mute Members',
    'deafen_members': 'Deafen Members',
    'move_members': 'Move Members',
    'use_voice_activation': 'Use Voice Activity',
    'change_nickname': 'Change Nickname',
    'manage_nicknames': 'Manage Nicknames',
    'manage_roles': 'Manage Roles',
    'manage_webhooks': 'Manage Webhooks',
    'manage_emojis': 'Manage Emojis'
}

USED_OPTIONS = ['args', 'suffix', 'clean_args', 'clean_suffix', 'cmd']


class Context:
    '''
    Custom object that get's passed to commands.
    Not intended to be created manually.
    '''
    def __init__(self, msg: discord.Message, amethyst: discord.Client):
        cleaned = message_parsing.parse_prefixes(msg.content, amethyst.config['AMETHYST_PREFIXES'])
        self.msg = msg
        self.cmd = message_parsing.get_cmd(cleaned)
        self.suffix, self.args = message_parsing.get_args(cleaned)

    async def __send__(self, content, dest, *, embed=None, file=None, files=None):
        '''Internal send function, not actually ment to be used by anyone.'''
        if dest == 'channel':
            return await self.msg.channel.send(content, embed=embed, file=file, files=files)
        elif dest == 'author':
            return await self.msg.author.send(content, embed=embed, file=file, files=files)
        else:
            raise ValueError('Destination is not `channel` or `author`.')

    async def send(self, content: str=None,
                   *, dest: str='channel',
                   embed: discord.Embed=None, file: discord.File=None,
                   files: List[discord.File]=None):
        '''Sends a message to the context origin, can either be the channel or author.'''
        if content is None and not embed and not file and not files:
            raise TypeError('No content and no attachments.')
        elif content:
            # Escape bad mentions
            content = str(content).replace('@everyone', '@\u200Beveryone').replace('@here', '@\u200Bhere')

        msg = None

        # Splitting messages if they are larger than 2000 chars.
        # Also properly does codeblocks.
        # (Could be done nicer but eh)
        if content and len(content) > 2000:
            if content.find('```') == -1 or content.find('```', content.find('```') + 3) == -1:
                await self.__send__(content[:2000], dest, embed=embed, file=file, files=files)
                await self.send(content[2000:], dest=dest)
            elif content.find('```', content.find('```') + 3) + 2 < 2000:
                await self.__send__(content[:content.find('```', content.find('```') + 3) + 3], dest,
                                    embed=embed, file=file, files=files)
                await self.send(content[content.find('```', content.find('```') + 3) + 3:], dest=dest)
            else:
                start_block = content[content.find('```'):content.find('\n', content.find('```')) + 1]

                if content.find('\n', content.find('```')) == content.rfind('\n', 0, 2000):
                    split_cont = content[:1996] + '\n```'
                    content = start_block + content[1996:]
                else:
                    split_cont = content[:content.rfind('\n', 0, content.rfind('\n', 0, 2000) + 1)][:1996] + '\n```'
                    content = start_block + content[len(split_cont) - 4:]

                await self.send(split_cont + content, dest=dest, embed=embed, file=file, files=files)
        else:
            msg = await self.__send__(content, dest, embed=embed, file=file, files=files)

        return msg

    def is_dm(self):
        '''Checks if the channel for the context is a DM or not.'''
        return isinstance(self.msg.channel, discord.DMChannel)

    def has_permission(self, permission, who='self'):
        """Check if someone in context has a permission."""
        if who not in ['self', 'author']:
            raise ValueError('Invalid value for `who` (must be `self` or `author`).')

        if permission not in PRETTY_PRINTED_PERMS:
            return False

        if who == 'self':
            return getattr(self.msg.channel.permissions_for(self.msg.guild.me), permission)
        elif who == 'author':
            return getattr(self.msg.channel.permissions_for(self.msg.author), permission)

    def typing(self):
        return ContextTyping(self)


class Command:
    '''Represents a command.'''
    def __init__(self, func: Callable[..., None],
                 *, name: str=None, description: str = '',
                 aliases: list = [], usage: str = '',):
        self.func = func
        self.name = name or func.__name__
        self.description = description or inspect.cleandoc(func.__doc__ or '')
        self.short_description = self.description.split('\n')[0]
        self.usage = usage
        self.aliases = aliases or []
        self.cls = None
        self.checks = func._checks if '_checks' in dir(func) else []

    def __repr__(self) -> str:
        return self.name

    async def run(self, ctx: Context) -> None:
        '''Runs a command, taking into account the checks for the command.'''
        if not self.checks:
            await self.func(self.cls, ctx)
        else:
            can_run = True

            for check in self.checks:
                if inspect.iscoroutinefunction(check):
                    res = await check(ctx)
                else:
                    res = check(ctx)

                if not res:
                    can_run = False
                    break

            if can_run:
                await self.func(self.cls, ctx)


class CommandGroup(Command):
    '''Represents a command that contains additional commands as subcommands.'''
    def __init__(self, func, **attrs):
        super().__init__(func, **attrs)
        self.all_commands = {}

    @property
    def commands(self) -> Set[Command]:
        '''Set of all unique commands and aliases in the group.'''
        return set(self.all_commands.values())

    def add_command(self, cmd):
        '''
        Adds a command to the group.
        You should use the command decorator.
        '''
        if not isinstance(cmd, Command):
            raise TypeError("Passed command isn't a Command instance.")

        if cmd.name in self.all_commands:
            raise AttributeError(f'Command `{cmd.name}` is already registered.')

        cmd.parent = self
        self.all_commands[cmd.name] = cmd

        for alias in cmd.aliases:
            if alias in self.all_commands:
                raise AttributeError(f'Aliases or command `{cmd.name}` is already registed.')

            self.all_commands[alias] = cmd

    async def run(self, ctx: Context) -> None:
        '''
        Runs the main command, or a subcommand, taking into account the group's checks, and the subcommand's checks.
        '''
        if not ctx.args or ctx.args[0] not in self.all_commands:
            if not self.checks:
                await self.func(self.cls, ctx)
            else:
                can_run = True

                for check in self.checks:
                    if inspect.iscoroutinefunction(check):
                        res = await check(ctx)
                    else:
                        res = check(ctx)

                    if not res:
                        can_run = False
                        break

                if can_run:
                    await self.func(self.cls, ctx)
        else:
            cmd = self.all_commands[ctx.args[0]]
            ctx.suffix = ctx.suffix.split(' ', 1)[1:]
            ctx.cmd += ' ' + ctx.args[0]

            if ctx.suffix:
                ctx.suffix = ctx.suffix[0]
            else:
                ctx.suffix = ''

            del ctx.args[0]

            if not self.checks:
                await cmd.run(ctx)
            else:
                # Obey the parent's checks if they have an.
                can_run = True

                for check in self.checks:
                    if inspect.iscoroutinefunction(check):
                        res = await check(ctx)
                    else:
                        res = check(ctx)

                    if not res:
                        can_run = False
                        break

                if can_run:
                    await cmd.run(ctx)

    def command(self, **attrs):
        '''Decorator to add a command into the group.'''
        def decorator(func):
            res = command(**attrs)(func)

            self.add_command(res)
            return res

        return decorator


class CommandHolder:
    '''Object that holds commands and aliases, as well as managing the loading and unloading of modules.'''
    def __init__(self, amethyst):
        self.commands = {}
        self.aliases = {}
        self.modules = {}
        self.amethyst = amethyst

    def __len__(self):
        return len(self.commands)

    def __contains__(self, x: str) -> bool:
        return x in self.commands

    def load_module(self, module_name: str) -> None:
        '''Loads a module by name, and registers all its commands.'''
        if module_name in self.modules:
            raise Exception(f'Module `{module_name}` is already loaded.')

        module = getattr(__import__(module_name), module_name.split('.')[-1])

        try:
            module.setup
        except AttributeError:
            del sys.modules[module_name]
            raise Exception('Module does not have a `setup` function.')

        module = module.setup(self.amethyst)
        cmds = [x for x in dir(module) if not re.match('__?.*(?:__)?', x) and isinstance(getattr(module, x), Command)]
        loaded_cmds = []
        loaded_aliases = []

        if not cmds:
            del sys.modules[module_name]
            raise ValueError('Module is empty.')

        for cmd in cmds:
            cmd = getattr(module, cmd)

            if not isinstance(cmd, Command):
                continue

            cmd.cls = module
            self.commands[cmd.name] = cmd

            for alias in cmd.aliases:
                self.aliases[alias] = self.commands[cmd.name]
                loaded_aliases.append(alias)

            loaded_cmds.append(cmd.name)

        self.modules[module_name] = loaded_cmds + loaded_aliases

    def reload_module(self, module_name: str) -> None:
        '''Reloads a module by name, and all its commands.'''
        if module_name not in self.modules:
            self.load_module(module_name)
            return

        self.unload_module(module_name)
        self.load_module(module_name)

    def unload_module(self, module_name: str) -> None:
        '''Unloads a module by name, and unregisters all its commands.'''
        if module_name not in self.modules:
            raise Exception(f'Module `{module_name}` is not loaded.')

        if hasattr(self.get_command(self.modules[module_name][0]).cls, '__unload'):
            self.get_command(self.modules[module_name][0]).cls.__unload()

        for cmd in self.modules[module_name]:
            if cmd in self.aliases:
                del self.aliases[cmd]
            elif cmd in self.commands:
                del self.commands[cmd]

        del self.modules[module_name]
        del sys.modules[module_name]

    def get_command(self, cmd_name: str) -> Union[Command, None]:
        '''Easily get a command via its name or alias'''
        return self.aliases[cmd_name] if cmd_name in self.aliases else\
            self.commands[cmd_name] if cmd_name in self.commands else None  # I wanted this to line up but fuck u pep8

    async def run_command(self, ctx: Context) -> None:
        cmd = self.get_command(ctx.cmd)

        if not cmd:
            return

        await cmd.run(ctx)

    @property
    def all_commands(self) -> List[str]:
        return sorted(self.commands.keys())

    @property
    def all_aliases(self) -> List[str]:
        return sorted(self.aliases.keys())

    @property
    def all_modules(self) -> List[str]:
        return sorted(self.modules.keys())


class ContextTyping:
    def __init__(self, ctx):
        self.loop = ctx.msg.channel._state.loop
        self.ctx = ctx

    async def do_typing(self):
        try:
            channel = self._channel
        except AttributeError:
            channel = self.ctx.msg.channel

        typing = channel._state.http.send_typing

        while True:
            await typing(channel.id)
            await asyncio.sleep(5)

    def __enter__(self):
        self.task = asyncio.ensure_future(self.do_typing(), loop=self.loop)
        self.task.add_done_callback(_typing_done_callback)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.task.cancel()

    async def __aenter__(self):
        self._channel = self.ctx.msg.channel

        await self._channel._state.http.send_typing(self._channel.id)
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb):
        self.task.cancel()


# Command conversion decorator
def command(**attrs):
    '''Decorator which converts a function into a command.'''
    def decorator(func):
        if isinstance(func, Command):
            raise TypeError('Function is already a command.')

        if not inspect.iscoroutinefunction(func):
            raise TypeError("Command function isn't a coroutine.")

        return Command(func, **attrs)

    return decorator


# Command group conversion decorator
def group(**attrs):
    '''Decorator which converts a function into a command group.'''
    def decorator(func):
        if isinstance(func, CommandGroup):
            raise TypeError('Function is already a command group.')
        elif isinstance(func, Command):
            raise TypeError('Function is already a command.')

        if not inspect.iscoroutinefunction(func):
            raise TypeError("Command function isn't a coroutine.")

        return CommandGroup(func, **attrs)

    return decorator


# Command checker convertor for decorators
def check(checker):
    def decorator(func):
        if isinstance(func, Command):
            func.checks.append(checker)
        else:
            if '_checks' not in dir(func):
                func._checks = []

            func._checks.append(checker)

        return func

    return decorator


# Some callback for typing
def _typing_done_callback(fut):
    try:
        fut.exception()
    except:
        pass
