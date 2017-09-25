"""
'Dusk' command system for Amethyst.
Based loosely (heh) off of discord.py's ext command system.
"""

from .context import Context  # NOQA
from .command import *  # NOQA
from .command_holder import CommandHolder  # NOQA
from .constants import *  # NOQA

__version__ = "1.0.0"
