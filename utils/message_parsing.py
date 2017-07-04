from typing import Tuple, List
import shlex


def get_cmd(string: str) -> str:
    '''Gets the command name from a string.'''
    return string.split(' ')[0]


def parse_prefixes(string: str, prefixes: List[str]) -> str:
    '''Cleans the prefixes off a string.'''
    for prefix in prefixes:
        if string.startswith(prefix):
            string = string[len(prefix):]
            break

    return string


def get_args(string: str) -> Tuple[str, str, Tuple[str, ...], Tuple[str, ...]]:
    '''Parses a message to get args and suffix.'''
    suffix = string.split(' ', 1)[1:]

    args = shlex.split(suffix.replace(r'\"', '\u009E').replace(r"\'", '\u009F'))
    args = [x.replace('\u009E', '"').replace('\u009F', "'") for x in args]

    return suffix, args
