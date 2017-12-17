from typing import Union, List
from discord.ext.commands import Paginator
from .command import Command, CommandGroup
from .context import Context
import importlib
import asyncio
import sys
import re

HIDDEN_RE = re.compile(r'^__?.*(?:__)?$')


async def handle_groups(self, paginator, ctx, cmd):
    longest = sorted(cmd.all_commands.values(), key=lambda x: len(x.name))[-1].name
    commands = sorted(cmd.all_commands.values(), key=lambda x: x.name)

    paginator.add_line(self.amethyst.config['AMETHYST_PREFIXES'][0] + cmd.name, empty=True)
    paginator.add_line(cmd.description or 'No description.', empty=True)
    paginator.add_line('Commands:')

    for cmd_ in commands:
        spacing = ' ' * (len(longest) - len(cmd_.name) + 1)
        line = f'  {cmd_.name}{spacing}{cmd_.short_description}'

        paginator.add_line(line)

    paginator.add_line('')

    if cmd.aliases:
        aliases = ', '.join(cmd.aliases)
        paginator.add_line(f'Aliases for this command are: {aliases}')

    paginator.add_line(f"Type {self.amethyst.config['AMETHYST_PREFIXES'][0]}{cmd.name} command, to run the command.")

    for page in paginator.pages:
        await ctx.send(page)
        await asyncio.sleep(.3333)


class CommandHolder:
    """Object that holds commands and aliases, as well as managing the loading and unloading of modules."""
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
        """Loads a module by name, and registers all its commands."""
        if module_name in self.modules:
            raise Exception(f'Module `{module_name}` is already loaded.')

        module = importlib.import_module(module_name)

        # Check if module has needed function
        try:
            module.setup
        except AttributeError:
            del sys.modules[module_name]
            raise Exception('Module does not have a `setup` function.')

        # Get class returned from setup.
        module = module.setup(self.amethyst)
        # Filter all class methods to only commands and those that do not have a parent (subcommands).
        cmds = [x for x in dir(module) if not HIDDEN_RE.match(x) and isinstance(getattr(module, x), Command)
                and not getattr(module, x).parent]
        loaded_cmds = []
        loaded_aliases = []

        if not cmds:
            del sys.modules[module_name]
            raise ValueError('Module is empty.')

        for cmd in cmds:
            # Get command from name
            cmd = getattr(module, cmd)

            # Ingore any non-commands if they got through, and subcommands
            if not isinstance(cmd, Command) or cmd.parent:
                continue

            # Give the command its parent class because it got ripped out.
            cmd.cls = module
            self.commands[cmd.name] = cmd

            # Generate usage for command.
            cmd._gen_usage()

            if isinstance(cmd, CommandGroup):
                for _cmd in cmd.commands:
                    # Take care of subcommands.
                    _cmd.cls = module

                    # Generate subcommand usage
                    _cmd._gen_usage()

            # Load aliases for the command
            for alias in cmd.aliases:
                self.aliases[alias] = self.commands[cmd.name]
                loaded_aliases.append(alias)

            loaded_cmds.append(cmd.name)

        self.modules[module_name] = loaded_cmds + loaded_aliases

    def reload_module(self, module_name: str) -> None:
        """Reloads a module by name, and all its commands."""
        if module_name not in self.modules:
            self.load_module(module_name)
            return

        self.unload_module(module_name)
        self.load_module(module_name)

    def unload_module(self, module_name: str) -> None:
        """Unloads a module by name, and unregisters all its commands."""
        if module_name not in self.modules:
            raise Exception(f'Module `{module_name}` is not loaded.')

        # Walk through the commands and remove them from the command and aliases dicts
        for cmd in self.modules[module_name]:
            if cmd in self.aliases:
                del self.aliases[cmd]
            elif cmd in self.commands:
                del self.commands[cmd]

        # Remove from self module array, and delete cache.
        del self.modules[module_name]
        del sys.modules[module_name]

    def get_command(self, cmd_name: str) -> Union[Command, None]:
        """Easily get a command via its name or alias"""
        return self.aliases[cmd_name] if cmd_name in self.aliases else\
            self.commands[cmd_name] if cmd_name in self.commands else None  # I wanted this to line up but fuck u pep8

    async def run_command(self, ctx: Context) -> None:
        cmd = self.get_command(ctx.cmd)

        if not cmd:
            return

        await cmd.run(ctx)

    async def send_cmd_help(self, ctx):
        """Sends the help for a command."""
        paginator = Paginator()
        prefixes = self.amethyst.config['AMETHYST_PREFIXES']

        if ' ' not in ctx.cmd:
            # Handle lone commands.
            cmd = self.get_command(ctx.cmd)

            if not cmd:
                return await ctx.send('Unknown command.')

            if cmd.name == 'help':
                # Show special block for help.
                longest = sorted(self.commands.values(), key=lambda x: len(x.name))[-1].name
                modules = set([self.get_command(x).cls.__class__.__name__ for x in self.commands])
                modules = sorted(modules)

                paginator.add_line(self.amethyst.tagline.format(self.amethyst.user.name), empty=True)

                for module in modules:
                    commands = [x for x in self.commands.values() if x.cls.__class__.__name__ == module and not x.parent]
                    commands = sorted(commands, key=lambda x: x.name)

                    if str(ctx.msg.author.id) not in self.amethyst.owners:
                        commands = [x for x in commands if not x.hidden]

                    if commands:
                        paginator.add_line(module + ':')

                        for cmd_ in commands:
                            spacing = ' ' * (len(longest) - len(cmd_.name) + 1)
                            line = f'  {cmd_.name}{spacing}{cmd_.short_description}'

                            if len(line) > 80:
                                line = line[:77] + '...'

                            paginator.add_line(line)

                paginator.add_line('')
                paginator.add_line(f'Type {prefixes[0]}help command for more info on a command.')

                if len(prefixes) > 1:
                    extra_prefixes = ', '.join(f'"{x}"' for x in prefixes[1:])

                    paginator.add_line(f'Additional prefixes include: {extra_prefixes}')

                for page in paginator.pages:
                    await ctx.send(page, dest='author')
                    await asyncio.sleep(.333)
            else:
                if hasattr(cmd, 'commands'):
                    # Command is a group, display main help-like message.
                    await handle_groups(self, paginator, ctx, cmd)
                else:
                    # Regular command
                    paginator.add_line(f'{prefixes[0]}{cmd.name} {cmd.usage}', empty=True)
                    paginator.add_line(cmd.description or 'No description.')

                    if cmd.aliases:
                        aliases = ', '.join(cmd.aliases)

                        paginator.add_line('')
                        paginator.add_line(f'Aliases for this command are: {aliases}')

                    for page in paginator.pages:
                        await ctx.send(page)
                        await asyncio.sleep(.333)
        else:
            # Handles groups specially.
            cmds = ctx.cmd.split(' ')
            last = self.get_command(cmds[0])

            for cmd in cmds[1:]:
                if not cmd in last.all_commands:
                    return await ctx.send('Unknown command.')

                last = last.all_commands[cmd]

            paginator.add_line(f'{prefixes[0]}{ctx.cmd} {last.usage}', empty=True)
            paginator.add_line(last.description or 'No description.')

            if hasattr(last, 'commands'):
                # Handle groups
                return await handle_groups(self, paginator, ctx, last)

            if last.aliases:
                aliases = ', '.join(last.aliases)

                paginator.add_line('')
                paginator.add_line(f'Aliases for this command are: {aliases}')

            for page in paginator.pages:
                await ctx.send(page)
                await asyncio.sleep(.333)

    @property
    def all_commands(self) -> List[str]:
        return sorted(self.commands.keys())

    @property
    def all_aliases(self) -> List[str]:
        return sorted(self.aliases.keys())

    @property
    def all_modules(self) -> List[str]:
        return sorted(self.modules.keys())
