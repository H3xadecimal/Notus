import asyncio
import audioop
import functools
import time

import romkan
import discord
import youtube_dl as ytdl
from utils.tts import MaryTTS
from discord.ext import commands

from . import music_converters as conv


async def get_entry(song, opts, loop):
    with ytdl.YoutubeDL(opts) as dl:
        f = functools.partial(dl.extract_info, song, download=False)

    res = await loop.run_in_executor(None, f)

    try:
        res = res['entries'][0]
    except KeyError:
        pass

    # Create an entry
    entry = {
        'title': res["title"],
        'uploader': res.get('uploader'),
        'stream': res.get('is_live', False),
        'duration': res.get('duration'),
        'url': res['webpage_url'],
        'raw_url': res['url'],
    }

    return entry


class OverlaySource(discord.AudioSource):
    def __init__(self, source, overlay, player, *, vc):
        self.source = source
        self.player = player
        self.overlay = overlay
        self._overlay_source = discord.FFmpegPCMAudio(overlay)
        self.vc = vc
        self.vol = 1
        self.vol_step = .1

    def read(self):
        source_data = self.source.read()
        overlay_data = self._overlay_source.read()

        if not source_data:
            self.player.source = self._overlay_source
            self.vc.source = self._overlay_source
            self.cleanup()
            return overlay_data

        if not overlay_data:
            self.player.source = self.source
            self.vc.source = self.source
            self._overlay_source.cleanup()
            return source_data

        source_data = audioop.mul(source_data, 2, self.vol*(1-self.vol_step))
        overlay_data = audioop.mul(overlay_data, 2, self.vol*self.vol_step)

        return audioop.add(source_data, overlay_data, 2)

    def cleanup(self):
        self.source.cleanup()

    def vol_change_step(self):
        if self.vol_step < 1:
            self.vol_step += 0.05


class TTSOverlay(OverlaySource):
    def read(self):
        source_data = self.source.read()
        overlay_data = self._overlay_source.read()

        if not overlay_data:
            self.player.source = self.source
            self.vc.source = self.source
            self.cleanup()
            return source_data

        source_data = audioop.mul(source_data, 2, 0.2)
        overlay_data = audioop.mul(overlay_data, 2, 4)

        return audioop.add(source_data, overlay_data, 2)

    def cleanup(self):
        self._overlay_source.cleanup()


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

    def __init__(self, voice_client, channel, queue: str=None):
        self.vc = voice_client
        self.chan = channel
        self._queue = queue or []
        self.source = None

    async def queue(self, song, requester=None):
        if "youtube.com/playlist" in song:
            songs = await conv.youtube_playlist(song, requester,
                                                self.vc.loop)
            self._queue += songs
            return await self.chan.send("Added {} items to the queue!"
                                        .format(len(songs)))

        if all(x in song for x in ["soundcloud.com", "/sets/"]):
            songs = await conv.soundcloud_playlist(song, requester,
                                                   self.vc.loop)
            self._queue += songs
            return await self.chan.send("Added {} items to the queue!"
                                        .format(len(songs)))

        if "bandcamp.com/album" in song:
            songs = await conv.bandcamp_playlist(song, requester,
                                                 self.vc.loop)
            self._queue += songs
            return await self.chan.send("Added {} items to the queue!"
                                        .format(len(songs)))

        entry = await get_entry(song, self.opts, self.vc.loop)
        entry["requester"] = requester
        if entry["duration"] is None:
            return await self.chan.send("Song has no duration, not queueing!")
        self._queue.append(entry)
        await self.chan.send('Added {} to the queue!'.format(entry['title']))

    async def download_next(self):
        next = self._queue.pop(0)

        await self.chan.send('Now Playing: {}'.format(next['title']))
        entry = await get_entry(next['url'], self.opts, self.vc.loop)
        dl_url = entry['raw_url']

        self._start_time = time.time()

        self.current_song = next

        if self.source is not None:
            self.source = OverlaySource(self.source, dl_url, self, vc=self.vc)
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
                    " - ": ", ",
                    "ft.": "featuring",
                    "official audio": "",
                    "official video": "",
                    "official music video": "",
                    "free download": "",
                    "audio": ""
                }

                t = romkan.to_roma(next['title']).lower()
                for c, r in replaces.items():
                    t = t.replace(c, r)
                t = "".join(c for c in t if c in can_pronounce)
                data = await self.tts._say('Now Playing: {}'.format(t),
                                           voice="dfki-prudence")
                with open(source, "wb") as f:
                    f.write(data)
                self.source = TTSOverlay(self.source, source, self, vc=self.vc)
                self.vc.source = self.source
            except:
                pass
        else:
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(dl_url),
                volume=0.5)
            self.source = source
            self.vc.play(source, after=self.skip)

    def start(self):
        self._stop = False
        self._skip = False
        self._task = self.vc.loop.create_task(self.process_queue())

    async def stop(self):
        self._stop = True
        self._task.cancel()
        await self.vc.disconnect()
        self.vc.stop()
        self._queue.clear()

    def skip(self, e=None):
        if e is not None:
            print(e)
        self._skip = True

    async def process_queue(self):
        await self.download_next()
        queue_next = True

        while True:
            if self._stop:
                break

            await asyncio.sleep(1)
            try:
                if self.current_song['stream']:
                    # Streams have no duration
                    continue
            except AttributeError:
                # current_song not yet loaded
                continue

            now = time.time()
            time_left = self.current_song['duration'] - (now-self._start_time)
            self.percentage = 1 - (time_left / self.current_song['duration'])
            if time_left <= 10 or self._skip:
                if queue_next is False and not self._skip:
                    continue

                if self._skip:
                    self._skip = False

                queue_next = False
                # Less than 10 seconds left until
                # the song ends, start the next song.
                if len(self._queue) > 0:
                    # There are still songs queued

                    # This data will mix with the data in the previous thread,
                    # Not sure if this will mess up but we'll see how it goes
                    await self.download_next()
                    now = time.time()
                    time_left = (self.current_song['duration'] -
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
                    self.source = TTSOverlay(self.source, source,
                                             self, vc=self.vc)
                    self.vc.source = self.source
                    await self.stop()

            else:
                queue_next = True


class music:
    def __init__(self, amethyst):
        self.amethyst = amethyst
        self.players = {}
        self.queues = {}

    @commands.command(name='play')
    async def music_play(self, ctx, *, song: str):
        start = False
        if ctx.guild.id not in self.players:
            vc = await ctx.author.voice.channel.connect(reconnect=True)
            self.queues[ctx.guild.id] = []
            self.players[ctx.guild.id] = Player(vc, ctx.channel,
                                                self.queues[ctx.guild.id])
            start = True

        await self.players[ctx.guild.id].queue(song, requester=ctx.author)

        if start:
            self.players[ctx.guild.id].start()

    @commands.command(name='queue')
    async def music_playlist(self, ctx):
        await ctx.send('\n'.join(s['name'] for s in self.queues[ctx.guild.id]))

    @commands.command(name="disconnect")
    async def music_disconnect(self, ctx):
        await self.players[ctx.guild.id].stop()
        del self.players[ctx.guild.id]
        del self.queues[ctx.guild.id]

    @commands.command(name="song")
    async def music_current_song(self, ctx):
        song = self.players[ctx.guild.id].current_song
        title = song["title"]
        url = song["url"]
        req = str(song["requester"])
        upl = song["uploader"]
        perc = self.players[ctx.guild.id].percentage
        prog = "#"*round(perc*10)+"-"*round((1-perc)*10)

        e = discord.Embed(title="Now Playing",
                          description=title)

        e.add_field(name="Source", value="[Click here!]({})".format(url))
        e.add_field(name="Progress", value="`[{}]` - {}%".format(
                prog, round(perc*100)))
        e.add_field(name="Uploaded by", value=upl, inline=True)
        e.add_field(name="Requested by", value=req, inline=True)

        await ctx.send(embed=e)


def setup(amethyst):
    amethyst.add_cog(music(amethyst))
