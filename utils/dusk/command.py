from typing import Callable, List, Tuple, Set
from .context import Context
import inspect

POS = inspect.Parameter.VAR_POSITIONAL
KW = inspect.Parameter.KEYWORD_ONLY
EMPTY = inspect.Parameter.empty
IS_UNION = lambda x: x.__class__.__name__ == '_Union'  # noqa (I ain't dealing with ur crap flake8)


class Command:
    """Represents a command."""
    def __init__(self, func: Callable[..., None],
                 *, name: str=None, description: str='',
                 aliases: List[str]=[], usage: str='', cls=None):
        self.func = func
        self.name = name or func.__name__
        self.description = description or inspect.cleandoc(func.__doc__ or '')
        self.short_description = self.description.split('\n')[0]
        self.aliases = aliases or []
        self.cls = cls
        self.checks = getattr(func, '_checks', [])
        self.hidden = getattr(func, '_hidden', False)
        self.usage = usage
        self.parent = None

    def __repr__(self) -> str:
        return self.name

    def _gen_usage(self):
        """
        Automatically generates usage text for the command if it has kwargs.
        Will not run if the command already has a usage.

        Output will look like this:
            <foo: integer> Required argument with a type.
            <foo: integer (multiple)> Required argument with a type and multiple (*foo)
            <foo (multiple)> Required arugment with only a multiple
            [foo: integer] Optional argument with a type
            [foo: integer (multiple)] Optional argument with a type and multiple (*foo)
            [foo (multiple)] Optional argument with only a multiple.

        "Real world" examples:
            <owners: user (multiple)>
            <user: user> [reason: string]
        """
        sig = inspect.signature(self.func)

        if not self.usage and list(sig.parameters.items())[2:]:
            func_args = list(sig.parameters.items())[2:]
            usage = ''

            for arg in func_args:
                format_args = [arg[0], '', '']

                if arg[1].kind == inspect.Parameter.VAR_POSITIONAL:
                    format_args[2] = ' (multiple)'

                if arg[1].annotation is not inspect.Parameter.empty:
                    if arg[1].annotation.__class__.__name__ == '_Union':
                        pass
                    else:
                        type = self.cls.amethyst.converters.arg_complaints[arg[1].annotation].expected
                        format_args[1] = f': {type}'

                if arg[1].default is not inspect.Parameter.empty:
                    usage += f' <{format_args[0]}{format_args[1]}{format_args[2]}>'
                else:
                    usage += f' [{format_args[0]}{format_args[1]}{format_args[2]}]'

            self.usage = usage.strip()

    async def run(self, ctx: Context) -> None:
        """
        Runs a command, taking into account the checks for the command.
        This will also automatically convert arguments if the command has need for it.
        """
        if not self.checks:
            sig = inspect.signature(self.func).parameters

            if len(sig) == 2:
                await self.func(self.cls, ctx)
            else:
                args, kwargs = await self.proc_args(ctx)

                # Processing arguments most likely failed. Return so that the command doesn't get triggered.
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
                    args, kwargs = await self.proc_args(ctx)

                    # Processing arguments most likely failed. Return so that the command doesn't get triggered.
                    if not args and not kwargs:
                        return

                    await self.func(self.cls, ctx, *args, **kwargs)

    async def proc_args(self, ctx: Context) -> Tuple[list, dict]:
        """
        Proccess extra arguments for the command if it has them, obeying the types and defaults that have them.
        Any arguments that do not have a type hint will be automatically defaulted to `str`.

        There shouldn't be any real reason to use this on your own.
        """
        args = list(inspect.signature(self.func).parameters.items())[2:]  # Stupid iterator subclass things
        pos_args = []
        kw_args = {}
        amethyst = self.cls.amethyst  # noqa Maybe find some better way of getting an Amethyst instance or converters, this is too reliant on the end user.
        has_pos = False
        has_kw = False

        if not args:
            return [], {}

        # Multi positional arguments (*varargs)
        if args[0][1].kind == POS:
            has_pos = True
            arg = args.pop(0)
            ctx_pos = ctx.args[:-len(args)]
            arg_type = arg[1].annotation if arg[1].annotation is not EMPTY else str
            arg_type = arg_type._subs_tree()[1:] if IS_UNION(arg_type) else arg_type

            for pos in ctx_pos:
                if type(arg_type) == list:  # Union
                    for utype in arg_type:
                        _arg = await amethyst.converters.convert_arg(ctx, pos, utype)

                        if _arg or _arg is False:
                            break
                else:
                    _arg = await amethyst.converters.convert_arg(ctx, pos, arg_type)

                pos_args.append(_arg)

        # Keyword arguments (*, kwarg=None)
        if args and args[0][1].kind == KW:
            ctx_kw = ctx.args[-len(args):] if has_pos else ctx.args
            has_kw = True

            for i, kw in enumerate(args):
                arg_type = kw[1].annotation if kw[1].annotation != EMPTY else str
                arg_type = arg_type._subs_tree()[1:] if IS_UNION(arg_type) else arg_type

                if type(arg_type) == list:  # Union
                    for utype in arg_type:
                        _arg = await amethyst.converters.convert_arg(ctx, ctx_kw[i], utype)

                        if _arg or _arg is False:
                            break
                else:
                    _arg = await amethyst.converters.convert_arg(ctx, ctx_kw[i], arg_type)

                kw_args[kw[0]] = _arg
        else:
            raise ValueError(f'Unknown or unsupported argument type: {args[0][1].kind.name}')

        # Handle any positional arguments that have the wrong type.
        # Blame flake8 for the shitty indentation
        if has_pos and arg[1].annotation not in (EMPTY, str) and ([x for x in pos_args if not isinstance(x,
                                                                   arg[1].annotation)] or not pos_args):
            await ctx.send(amethyst.converters.complaints[arg[1].annotation])
            return [], {}

        # Handle keyword arguments with wrong types.
        if has_kw and len(kw_args) == len(args):
            invalids = [arg for arg in args if arg[1].annotation != EMPTY and
                        not isinstance(kw_args[arg[0]], arg[1].annotation)]

            if invalids:
                first = invalids[0]
                msg = amethyst.converters.complaints[first[1].annotation]

                await ctx.send(f'Error for argument `{first[1]}` for command `{ctx.cmd}`\n```{msg}```')
                return [], {}
        elif has_kw:  # Handle missing arguments that do not have a default.
            missing_args = [x for x in args[len(kw_args):] if x[1].default == EMPTY]

            if missing_args:
                first = missing_args[0]
                atype = first[1].annotation if first[1].annotation != EMPTY else str
                atype = amethyst.converters.complaints[atype].expected

                await ctx.send(f'Missing argument `{first[0]}` for command `{ctx.cmd}`.\nThis should be a {atype}')
                return [], {}

        return pos_args, kw_args


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
                    args, kwargs = await self.proc_args(ctx)

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
                        args, kwargs = await self.proc_args(ctx)

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


# Command conversion decorator
def command(**attrs):
    """Decorator which converts a function into a command."""
    def decorator(func):
        if isinstance(func, Command):
            raise TypeError('Function is already a command.')

        if not inspect.iscoroutinefunction(func):
            raise TypeError("Command function isn't a coroutine.")

        return Command(func, **attrs)

    return decorator


# Command group conversion decorator
def group(**attrs):
    """Decorator which converts a function into a command group."""
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
def check(checker, hide=None):
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
    def decorator(func):
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
def hidden():
    """Decorator to quickly hide a command."""
    def decorator(func):
        if isinstance(func, Command):
            func.hidden = True
        else:
            func._hidden = True

        return func

    return decorator
