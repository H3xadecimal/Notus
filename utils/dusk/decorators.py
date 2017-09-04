from typing import Callable, Union
from .command import Command
from .command_group import CommandGroup
from .context import Context
import inspect


# Command conversion decorator
def command(**attrs) -> Callable[Callable, Command]:
    """Decorator which converts a function into a command."""
    def decorator(func: Callable) -> Command:
        if isinstance(func, Command):
            raise TypeError('Function is already a command.')

        if not inspect.iscoroutinefunction(func):
            raise TypeError("Command function isn't a coroutine.")

        return Command(func, **attrs)

    return decorator


# Command group conversion decorator
def group(**attrs) -> Callable[Callable, CommandGroup]:
    """Decorator which converts a function into a command group."""
    def decorator(func: Callable) -> CommandGroup:
        if isinstance(func, CommandGroup):
            raise TypeError('Function is already a command group.')
        elif isinstance(func, Command):
            raise TypeError('Function is already a command.')

        if not inspect.iscoroutinefunction(func):
            raise TypeError("Command function isn't a coroutine.")

        return CommandGroup(func, **attrs)

    return decorator


# Command checker convertor for decorators
def check(checker: Callable[Context, bool], hide: bool=None) -> Callable[Callable, Union[Command, Callable]]:
    """
    Wrapper to make a checker for a command.
    Your checker function should look something like this:
    ```py
    def my_checker():
        def checker(ctx):
            return Boolean statement (eg. True, ctx.blah == 'blah')

        return check(checker)
    ```
    After which, you can then use it like.
    ```py
    from my_confirms_file import my_checker

    ...

    class Blah:
        ...
        @command()
        @my_checker()
        async def checked_command(self, ctx):
            ...
    """
    def decorator(func: Callable) -> Union[Callable, Command]:
        if isinstance(func, Command):
            func.checks.append(checker)

            if hide is True:
                func = hidden()(func)
        else:
            if not hasattr(func, '_checks'):
                func._checks = []

            func._checks.append(checker)

            if hide is True:
                func = hidden()(func)

        return func

    return decorator


# Command hider decorator
def hidden() -> Callable:
    """Decorator to quickly hide a command."""
    def decorator(func: Callable) -> Union[Callable, Command]:
        if isinstance(func, Command):
            func.hidden = True
        else:
            func._hidden = True

        return func

    return decorator
