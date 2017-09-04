from typing import Callable, List, Tuple
from .context import Context
from utils.arg_converters import InvalidArg
import inspect


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
                args, kwargs = await self.process_extra_args(ctx)

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
                    args, kwargs = await self.process_extra_args(ctx)

                    # Processing arguments most likely failed. Return so that the command doesn't get triggered.
                    if not args and not kwargs:
                        return

                    await self.func(self.cls, ctx, *args, **kwargs)

    async def process_extra_args(self, ctx: Context) -> Tuple[list, dict]:
        """
        Processes extra arguments for commands that need them, obeying types and defaults.
        Any arguments that do not have a type hint will be defaulted to `str`.

        Should work for commands like this:
            async def command(self, ctx, *foo: int)
            async def command(self, ctx, *, kw_arg_one: discord.Member, kw_arg_two: int=None, etc)
            async def command(self, ctx, *bunch_of_numbers: int, kw_arg_one: discord.Channel, kw_arg_two: whatever)

        Probably best to not use this by itself unless you know what you're doing.
        """
        func_args = list(inspect.signature(self.func).parameters.items())[2:]  # Get all extra args from func.
        varargs = []
        kwargs = {}
        amethyst = self.cls.amethyst

        # Logic for if there is a vararg parameter (eg. *args)
        if func_args[0][1].kind == inspect.Parameter.VAR_POSITIONAL:
            # Get kwargs without the vararg and vice-versa
            kw_args = func_args[1:]
            var_args = func_args[0][1]
            # Get last n args as the kwargs, with the rest being used for varargs
            if kw_args:
                ctx_kw_args = ctx.args[-len(kw_args):]
                ctx_var_args = ctx.args[:-len(kw_args)]
            else:
                ctx_var_args = ctx.args
            # Get wanted type from annotation, otherwise default to str
            var_arg_cls = var_args.annotation if var_args.annotation is not inspect.Parameter.empty else str

            # Convert varargs
            for arg in ctx_var_args:
                # Handle Union types
                if var_arg_cls.__class__.__name__ == '_Union':
                    # Gotta love the ol' dir(class) to find internal methods
                    union_types = var_arg_cls._subs_tree()[1:]

                    for utype in union_types:
                        arg = await amethyst.converters.convert_arg(ctx, arg, utype)

                        if arg or arg is False:
                            break
                else:
                    arg = await amethyst.converters.convert_arg(ctx, arg, var_arg_cls)

                varargs.append(arg)

            # Convert kwargs
            if kw_args:
                for arg in ctx_kw_args:
                    i = ctx_kw_args.index(arg)
                    kw_arg = kw_args[i][1]
                    arg_cls = kw_arg.annotation if kw_arg.annotation is not inspect.Parameter.empty else str

                    # Handle Union types
                    if arg_cls.__class__.__name__ == '_Union':
                        # Gotta love the ol' dir(class) to find internal methods
                        union_types = arg_cls._subs_tree()[1:]

                        for utype in union_types:
                            arg = await amethyst.converters.convert_arg(ctx, arg, utype)

                            if arg or arg is False:
                                break
                    else:
                        arg = await amethyst.converters.convert_arg(ctx, arg, arg_cls)

                    kwargs[kw_args[i][0]] = arg
        else:
            ctx_kw_args = ctx.args[:len(func_args)]

            for arg in ctx_kw_args:
                i = ctx_kw_args.index(arg)
                kw_arg = func_args[i][1]
                arg_cls = kw_arg.annotation if kw_arg.annotation is not inspect.Parameter.empty else str

                # Handle Union types
                if arg_cls.__class__.__name__ == '_Union':
                    # Gotta love the ol' dir(class) to find internal methods
                    union_types = arg_cls._subs_tree()[1:]

                    for utype in union_types:
                        arg = await amethyst.converters.convert_arg(ctx, arg, utype)

                        if arg or arg is False:
                            break
                else:
                    arg = await amethyst.converters.convert_arg(ctx, arg, arg_cls)

                kwargs[func_args[i][0]] = arg

        # If the first argument is a vararg, and it doesn't have a default, and it has an annotation,
        # handle invalid arguments  # HAHA FUCK YOU PEP8 LET ME HAVE LONG ASS COMMENTS
        if (func_args[0][1].kind == inspect.Parameter.VAR_POSITIONAL and
                func_args[0][1].default is inspect.Parameter.empty and
                func_args[0][1].annotation is not inspect.Parameter.empty):
            expected_type = func_args[0][1].annotation
            # Get any invalid varargs
            invalid_type_varargs = [x for x in varargs if not isinstance(x, expected_type)]

            if not varargs or invalid_type_varargs:
                invalid_msg = amethyst.converters.arg_complaints[expected_type]

                await ctx.send(invalid_msg)

                return [], {}

        # Ditto for kwargs
        if kwargs:
            all_kw_args = [x for x in func_args if x[1].kind == inspect.Parameter.KEYWORD_ONLY]

            if len(kwargs) == len(all_kw_args):
                first_invalid = None

                for arg in all_kw_args:
                    if arg[1].annotation is inspect.Parameter.empty:
                        continue

                    i = all_kw_args.index(arg)

                    if not isinstance(list(kwargs.items())[i][1], arg[1].annotation):
                        first_invalid = i
                        break

                if first_invalid is not None:
                    user_arg = list(kwargs.items())[i]
                    wanted_type = all_kw_args[i].annotation

                    if isinstance(user_arg[1], InvalidArg):
                        await ctx.send(f'Error for argument `{user_arg[0]}` for command `{ctx.cmd}`:\n{user_arg[1]}')

                        return [], {}
                    else:
                        invalid_msg = amethyst.converters.arg_complaints[wanted_type]

                        await ctx.send(f'Error for argument `{user_arg[0]}` for command `{ctx.cmd}`:\n{invalid_msg}')

                        return [], {}
            else:
                missing_args = all_kw_args[len(kwargs):]
                missing_arg = None

                for arg in missing_args:
                    if arg[1].default is inspect.Parameter.empty:
                        missing_arg = arg
                        break

                if missing_arg is None:
                    return varargs, kwargs
                else:
                    await ctx.send(f'Missing argument `{missing_arg[1].name}`.')

                    return [], {}

        return varargs, kwargs
