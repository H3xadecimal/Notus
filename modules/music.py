import asyncio
import audioop
import functools
import time

import discord
import youtube_dl as ytdl
from discord.ext import commands


def music_after(e):
    print(e)

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

        source_data = audioop.mul(source_data, 2, self.vol*(1-self.vol_step))
        overlay_data = audioop.mul(overlay_data, 2, self.vol*self.vol_step)

        return audioop.add(source_data, overlay_data, 2)

    def cleanup(self):
        self.source.cleanup()

    def vol_change_step(self):
        if self.vol_step < 1:
            self.vol_step += 0.1


class Player:
    opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'audioformat': 'flac',
        'quiet': True,
        'default_search': 'auto'
    }

    def __init__(self, voice_client, channel, queue: str=None):
        self.vc = voice_client
        self.chan = channel
        self._queue = queue or []
        self.source = None

    async def queue(self, song, requester=None):
        entry = await get_entry(song, self.opts, self.vc.loop)
        entry["requester"] = requester
        if entry["duration"] is None:
            return await self.chan.send("Song has no duration, not queueing!")
        self._queue.append(entry)
        await self.chan.send('Added {} to the queue!'.format(entry['title']))

    async def download_next(self):
        next = self._queue.pop(0)

        await self.chan.send('Next up: {}'.format(next['title']))
        entry = await get_entry(next['url'], self.opts, self.vc.loop)
        dl_url = entry['raw_url']

        self._start_time = time.time()

        self.current_song = next

        if self.source is not None:
            self.source = OverlaySource(self.source, dl_url, self, vc=self.vc)
            self.vc.source = self.source
        else:
            source = discord.FFmpegPCMAudio(dl_url)
            self.source = source
            self.vc.play(source, after=self.stop)

    def start(self):
        self._stop = False
        self._task = self.vc.loop.create_task(self.process_queue())

    def stop(self, e=None):
        print(e)
        self._stop = True
        self._task.cancel()
        self.vc.stop()
        asyncio.run_coroutine_threadsafe(self.vc.disconnect(), self.vc.loop)
        self._queue.clear()

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
            if time_left <= 5:
                if queue_next is False:
                    continue
                queue_next = False
                # Less than 10 seconds left until
                # the song ends, start the next song.
                if len(self._queue) > 0:
                    # There are still songs queued

                    # This data will mix with the data in the previous thread,
                    # Not sure if this will mess up but we'll see how it goes
                    await self.download_next()

                else:
                    await self.chan.send("Queue empty, stopping...")
                    await asyncio.sleep(time_left)

                for _ in range(round(time_left)-1):
                    self.source.vol_change_step()
                    self.source.vol_change_step()
                    await asyncio.sleep(0.5)

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
        self.players[ctx.guild.id].stop()
        await self.players[ctx.guild.id].vc.disconnect()

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
