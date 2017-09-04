from typing import List
from utils import message_parsing
from .constants import PERMISSIONS
import discord


class Context:
    """
    Custom object that get's passed to commands.
    Not intended to be created manually.
    """
    def __init__(self, msg: discord.Message, amethyst: discord.Client):
        cleaned = message_parsing.parse_prefixes(msg.content, amethyst.config['AMETHYST_PREFIXES'])
        self.msg = msg
        self.cmd = message_parsing.get_cmd(cleaned)
        self.suffix, self.args = message_parsing.get_args(cleaned)

    async def _send(self, content, dest, *, embed=None, file=None, files=None):
        """Internal send function, not actually ment to be used by anyone."""
        if dest == 'channel':
            return await self.msg.channel.send(content, embed=embed, file=file, files=files)
        elif dest == 'author':
            return await self.msg.author.send(content, embed=embed, file=file, files=files)
        else:
            raise ValueError('Destination is not `channel` or `author`.')

    async def send(self, content: str=None,
                   *, dest: str='channel',
                   embed: discord.Embed=None, file: discord.File=None,
                   files: List[discord.File]=None) -> discord.Message:
        """Sends a message to the context origin, can either be the channel or author."""
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
                await self._send(content[:2000], dest, embed=embed, file=file, files=files)
                await self.send(content[2000:], dest=dest)
            elif content.find('```', content.find('```') + 3) + 2 < 2000:
                await self._send(content[:content.find('```', content.find('```') + 3) + 3], dest,
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
            msg = await self._send(content, dest, embed=embed, file=file, files=files)

        return msg

    def is_dm(self) -> bool:
        """Check if the channel for the context is a DM or not."""
        return isinstance(self.msg.channel, discord.DMChannel)

    def has_permission(self, permission: str, who: str='self') -> bool:
        """Check if someone in context has a permission."""
        if who not in ['self', 'author']:
            raise ValueError('Invalid value for `who` (must be `self` or `author`).')

        if permission not in PERMISSIONS:
            return False

        if who == 'self':
            return getattr(self.msg.channel.permissions_for(self.msg.guild.me), permission)
        elif who == 'author':
            return getattr(self.msg.channel.permissions_for(self.msg.author), permission)

    def typing(self):
        """d.py `async with` shortcut for sending typing to a channel."""
        return self.msg.channel.typing()
