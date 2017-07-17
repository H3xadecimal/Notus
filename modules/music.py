import asyncio
import traceback
import time

import romkan
import discord
from utils.tts import MaryTTS
from utils.command_system import command

from . import music_sources as sources
from . import music_converters as conv


async def get_entry(song, loop):
    song = sources.YTDLSource(song, loop=loop)
    await song.load_data()

    return song


class Queue:
    def __init__(self, chunk_size: int=2, max_chunks: int=None,
                 max_per_user: int=None, unique: str=None,
                 silence_errors=False):
        self.size = chunk_size
        self.max = max_chunks
        self.user_max = max_per_user
        self.unique = unique
        self.silence_errors = silence_errors
        self.items = []
        self.current = []

    def _error(self, err):
        if not self.silence_errors:
            raise Exception(err)

    @property
    def queue(self):
        r = self.current[:]
        for group in self.items:
            r += group
        return r

    def __len__(self):
        return len(self.queue)

    def __repr__(self):
        return ("Queue(entries={1}, chunk_size={0.size}, "
                "max_chunks={0.max}, per_user={0.user_max}, "
                "unique={0.unique}, silent={0.silence_errors})").format(
                        self, len(self.queue))

    def show(self, source: str="title"):
        res = []
        for group in self.items:
            g = []
            for data in group:
                g.append({source: getattr(data, source),
                          "request_id": data.request_id})
            res.append(g)
        return res

    def add(self, items: list):
        errors = []
        for data in items:
            try:
                self.append(data)
            except Exception as e:
                errors[data.title] = e.args[0]
        return errors

    def append(self, item: sources.YTDLSource):
        # print("Adding:", item)
        # === LOGIC ===
        # Basically, the first thing is to find the index of the user's
        # last song (since when they add something new, it should always be
        # added after their other songs)
        # This is achieved by iterating backwards through the current queue,
        # stopping the first time something by that user is found
        # Next, we iterate forward from that starting point.
        # For each song, we put the user that added it into a set.
        # We continue to move forward this way until we hit a user that
        # is already in the set. We stop here and insert the item.

        # For users A, B, and C, imagine starting queue ABCABCABCBBBBB

        # User A tries to put something in the queue
        #       v last A, start here
        # ABCABCABCBBBBB
        # B goes into the set
        # C goes into the set
        # B is already in the set, so the A gets added here
        # ABCABCABCABBBBB

        # data["requester"] should have the `id` attribute,
        # this could be e.g. a discord.Member
        id = item.request_id

        if not self.items:
            self.items.append([item])
            return

        if len(self.items) == self.max:
            self._error("Max queue chunks reached.")

        if sum((chunk[0].request_id == id and
                len(chunk) == self.size)
                for chunk in self.items) == self.user_max:
            self._error("User reached maximum amount of chunks")

        # Check for dupes
        if self.unique is not None:
            for chunk in self.items:
                for item_u in chunk:
                    if (getattr(item_u, self.unique) ==
                            getattr(item, self.unique)):
                        self._error(
                            "Item already queued, `unique` key duplicate.")

        # Insert the data
        # print("Iterating backwards")
        for index, value in enumerate(reversed(self.items)):
            # print(index)
            if index == len(self.items)-1 or value[0].request_id == id:
                # we found the last item by us or
                # we have no items in the queue

                if value[0].request_id == id and len(value) < self.size:
                    # last item by us has a free space left
                    value.append(item)
                    return

                # index to start from
                # python is 0-indexed so subtract 1
                start = len(self.items) - index - 1
                found_ids = []

                # Easier than `enumerate` in this case
                # print("Iterating forward")
                while True:
                    # print(start)
                    if start >= len(self.items):
                        # print("Inserting at the end")
                        # No place left, put it at the end
                        self.items.append([item])
                        return

                    id = self.items[start][0].request_id

                    if id in found_ids:
                        # print("Duplicate found, inserting")
                        # this id appears for the second time now
                        # so insert here
                        self.items.insert(start, [item])
                        return

                    # Add the id to the list
                    found_ids.append(id)

                    start += 1

    def pop(self):
        if not self.current:
            # Load the next chunk
            # we use `pop` to make sure it disappears from the original list
            # because otherwise people could queue up forever
            self.current = self.items.pop(0)
        return self.current.pop(0)

    def clear(self):
        self.items.clear()
        self.current.clear()

    def shuffle(self, requester):
        s = []
        for i, chunk in enumerate(self.items):
            if chunk[0].requester == requester:
                chunk.shuffle()  # shuffle chunk items
                s.append(i)

        # shuffle chunks around
        s_c = s[:]
        s_c.shuffle()
        queue = self.items[:]
        for i in s:
            queue[i] = self.items[s_c[i]]

        self.items = queue


class Player:
    opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'audioformat': 'flac',
        'quiet': True,
        'default_search': 'auto'
    }

    try:
        tts = MaryTTS(enabled=True)
    except:
        # Voice not installed
        pass

    def __init__(self, voice_client, channel, cog):
        self.vc = voice_client
        self.chan = channel
        self._queue = Queue(unique="url")
        self.cog = cog
        self.source = None

    async def queue(self, song, requester=None):
        if "youtube.com/playlist" in song:
            songs = await conv.youtube_playlist(song, requester,
                                                self.vc.loop)
            errors = self._queue.add(songs)
            if errors:
                await self.chan.send("\n".join("{}: {}".format(t, e)
                                               for t, e in errors.items()))
            return await self.chan.send("Added {} items to the queue!"
                                        .format(len(songs)-len(errors)))

        if all(x in song for x in ["soundcloud.com", "/sets/"]):
            songs = await conv.soundcloud_playlist(song, requester,
                                                   self.vc.loop)
            errors = self._queue.add(songs)
            if errors:
                await self.chan.send("\n".join("{}: {}".format(t, e)
                                               for t, e in errors.items()))
            return await self.chan.send("Added {} items to the queue!"
                                        .format(len(songs)-len(errors)))

        if "bandcamp.com/album" in song:
            songs = await conv.bandcamp_playlist(song, requester,
                                                 self.vc.loop)
            errors = self._queue.add(songs)
            if errors:
                await self.chan.send("\n".join("{}: {}".format(t, e)
                                               for t, e in errors.items()))
            return await self.chan.send("Added {} items to the queue!"
                                        .format(len(songs)-len(errors)))

        if "osu.ppy.sh" in song:
            song = await conv.osu_song(song, requester, self.vc.loop)
            self._queue.append(song)
            await self.chan.send(
                    'Added {} to the queue!'.format(song['title']))

        entry = await get_entry(song, self.vc.loop)
        entry.set_requester(requester)
        if entry.duration is None:
            return await self.chan.send("Song has no duration, not queueing!")
        self._queue.append(entry)
        await self.chan.send('Added {} to the queue!'.format(entry.title))

    async def download_next(self):
        next = self._queue.pop()

        await self.chan.send('Now Playing: {}'.format(next.title))
        # print('Now Playing: {}'.format(next.title))
        await next.load()

        self._start_time = time.time()

        self.current_song = next

        if self.source is not None:
            self.source = sources.OverlaySource(self.source, next,
                                                self, vc=self.vc)
            self.vc.source = self.source

            try:
                source = "song_cache/{}.wav".format(self.chan.id)
                can_pronounce = (
                    "abcdefghijklmnopqrstuvwxyz"
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "0123456789 "
                )
                replaces = {
                    "&": "and",
                    " - ": ". ",
                    "ft.": "featuring",
                    "official audio": "",
                    "official video": "",
                    "official music video": "",
                    "free download": "",
                    "lyric video": "",
                    "audio": ""
                }

                t = romkan.to_roma(next.title).lower()
                for c, r in replaces.items():
                    t = t.replace(c, r)
                t = "".join(c for c in t if c in can_pronounce)
                # data = await self.tts._say('Now Playing: {}'.format(t),
                #                            voice="dfki-prudence")
                with open(source, "wb") as f:
                    f.write(data)
                self.source = sources.TTSOverlay(self.source, source,
                                                 self, vc=self.vc)
                self.vc.source = self.source
            except Exception as e:
                print(e)
        else:
            self.source = next
            self.vc.play(next, after=lambda: self.skip(e="errorskip"))

    def start(self):
        self._stop = False
        self._skip = False
        self._task = self.vc.loop.create_task(self.process_queue())

    async def stop(self):
        self._stop = True
        await self.vc.disconnect()
        self._task.cancel()
        self.vc.stop()
        self._queue.clear()
        del self.cog.players[self.chan.guild.id]

    def skip(self, e=None):
        if e is not None:
            print(e)

        if e == "errorskip":
            self.source = None
        self._skip = True

    async def process_queue(self):
        try:
            await self.download_next()
            queue_next = True

            while True:
                if self._stop:
                    break

                await asyncio.sleep(1)
                try:
                    if self.current_song.is_stream:
                        # Streams have no duration
                        continue
                except AttributeError as e:
                    # print(e, "No current song!")
                    # current_song not yet loaded
                    continue

                now = time.time()
                time_left = self.current_song.duration - (now-self._start_time)
                self.percentage = 1 - (time_left / self.current_song.duration)
                if time_left <= 20 or self._skip:
                    if queue_next is False and not self._skip:
                        # print("ignoring")
                        continue

                    if self._skip:
                        self._skip = False

                    queue_next = False
                    # Less than 20 seconds left until
                    # the song ends, start the next song.
                    if len(self._queue) > 0:
                        # There are still songs queued

                        if isinstance(self.source, sources.OverlaySource):
                            self.source = self.source._overlay_source
                            self.vc.source = self.source

                        # print("Downloading next song")
                        await self.download_next()
                        now = time.time()
                        time_left = (self.current_song.duration -
                                     (now-self._start_time))
                        for _ in range(round(time_left)*2):
                            try:
                                self.source.vol_change_step()
                                self.source.vol_change_step()
                                await asyncio.sleep(0.5)
                            except:
                                break

                    else:
                        await asyncio.sleep(time_left)
                        await self.chan.send("Queue empty, stopping...")
                        data = await self.tts._say('Queue empty, stopping...',
                                                   voice="dfki-prudence")
                        source = "song_cache/{}.wav".format(self.chan.id)
                        with open(source, "wb") as f:
                            f.write(data)
                        self.source = sources.TTSOverlay(self.source, source,
                                                         self, vc=self.vc)
                        self.vc.source = self.source
                        await self.stop()

                else:
                    queue_next = True
        except:
            traceback.print_exc()


class music:
    def __init__(self, amethyst):
        self.amethyst = amethyst
        self.players = {}

    @command(aliases=['play'], usage='[song]')
    async def music_play(self, ctx):
        song = ctx.suffix
        start = False
        if ctx.msg.guild.id not in self.players:
            vc = await ctx.msg.author.voice.channel.connect(reconnect=True)
            self.players[ctx.msg.guild.id] = Player(vc, ctx.msg.channel, self)
            start = True

        await self.players[ctx.msg.guild.id].queue(song, requester=ctx.msg.author)

        if start:
            self.players[ctx.msg.guild.id].start()

    @command(aliases=['queue'])
    async def music_playlist(self, ctx):
        player = self.players[ctx.msg.guild.id]
        queue = []
        for song in player._queue.queue:
            s = song.title
            if song.requester == ctx.msg.author:
                s = "**{}**".format(s)
            queue.append(s)

        t = ("**Now playing:** __{}__"
             "\n**Queue:** \n{}").format(
                     player.current_song.title,
                     "\n".join(queue))
        await ctx.send(t)

    @command(aliases=["disconnect"])
    async def music_disconnect(self, ctx):
        await self.players[ctx.msg.guild.id].stop()

    @command(aliases=["song"])
    async def music_current_song(self, ctx):
        song = self.players[ctx.msg.guild.id].current_song
        title = song.title
        url = song.url
        req = str(song.requester)
        upl = song.uploader
        perc = self.players[ctx.msg.guild.id].percentage
        prog = "#"*round(perc*10)+"-"*round((1-perc)*10)

        e = discord.Embed(title="Now Playing",
                          description=title)

        e.add_field(name="Source", value="[Click here!]({})".format(url))
        e.add_field(name="Progress", value="`[{}]` - {}%".format(
                prog, round(perc*100)))
        e.add_field(name="Uploaded by", value=upl, inline=True)
        e.add_field(name="Requested by", value=req, inline=True)

        if song.thumbnail:
            e.set_thumbnail(url=song.thumbnail)

        await ctx.send(embed=e)

    @command(aliases=['skip'])
    async def music_skip(self, ctx):
        if ctx.msg.author == self.players[ctx.msg.guild.id].current_song.requester:
            self.players[ctx.msg.guild.id].skip()
        else:
            await ctx.send("Skipping has only been implemented for the"
                           " person who queued the song.")


def setup(amethyst):
    return music(amethyst)
