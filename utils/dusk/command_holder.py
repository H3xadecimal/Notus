from typing import Union, List
from .command import Command, CommandGroup
from .context import Context
import importlib
import sys
import re

HIDDEN_RE = re.compile(r'^__?.*(?:__)?$')


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

    @property
    def all_commands(self) -> List[str]:
        return sorted(self.commands.keys())

    @property
    def all_aliases(self) -> List[str]:
        return sorted(self.aliases.keys())

    @property
    def all_modules(self) -> List[str]:
        return sorted(self.modules.keys())
