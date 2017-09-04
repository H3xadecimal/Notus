from typing import Set
from .command import Command
from .context import Context
from .decorators import command, group
import inspect


class CommandGroup(Command):
    """Represents a command that contains additional commands as subcommands."""
    def __init__(self, func, **attrs):
        super().__init__(func, **attrs)
        self.all_commands = {}

    @property
    def commands(self) -> Set[Command]:
        """Set of all unique commands and aliases in the group."""
        return set(self.all_commands.values())

    def add_command(self, cmd: Command):
        """
        Adds a command to the group.
        You should use the command decorator for ease-of-use.
        """
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
        """
        Runs the main command, or a subcommand, taking into account the group's checks, and the subcommand's checks.
        This will automatically convert any extra arguments for itself or a subcommand
        """
        if not ctx.args or ctx.args[0] not in self.all_commands:
            if not self.checks:
                sig = inspect.signature(self.func).parameters

                if len(sig) == 2:
                    await self.func(self.cls, ctx)
                else:
                    args, kwargs = await self.process_extra_args(ctx)

                    if not args and not kwargs:
                        return

                    await self.func(self.cls, ctx, *args, **kwargs)
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
                    sig = inspect.signature(self.func).parameters

                    if len(sig) == 2:
                        await self.func(self.cls, ctx)
                    else:
                        args, kwargs = await self.process_extra_args(ctx)

                        if not args and not kwargs:
                            return

                        await self.func(self.cls, ctx, *args, **kwargs)
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
        """Decorator to add a command into the group."""
        def decorator(func):
            res = command(**attrs)(func)

            self.add_command(res)
            return res

        return decorator

    def group(self, **attrs):
        """
        Decorator to add a group into the group.
        No man should have this much power.
        """
        def decorator(func):
            res = group(**attrs)(func)

            self.add_command(res)
            return res

        return decorator
