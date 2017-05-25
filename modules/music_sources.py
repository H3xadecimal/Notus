import audioop
import asyncio
import functools
import concurrent.futures

import discord
import youtube_dl as ytdl


class YTDLSource(discord.AudioSource):
    opts = {'format': 'bestaudio/best',
            'noplaylist': True,
            'audioformat': 'bestaudio/best',
            'quiet': True,
            'default_search': 'auto'}

    def __init__(self, query, volume=0.5, loop=None):
        self.query = query
        self.volume = volume
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.loop = loop or asyncio.get_event_loop()
        self._done = False

    def __repr__(self):
        return ("YTDLSource(title={0.title}, "
                "url={0.url}, volume={0.volume})").format(self)

    async def load_data(self):
        if not self._done:  # don't call it twice
            with ytdl.YoutubeDL(self.opts) as dl:
                f = functools.partial(dl.extract_info, self.query,
                                      download=False)

            data = await self.loop.run_in_executor(self.executor, f)
            if "entries" in data:
                data = data["entries"][0]
            self.set_data(data)

    def set_data(self, data):
        self.duration = data.get("duration")
        self.url = data.get("webpage_url")
        self.raw_url = data.get("url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = data.get("dislike_count")
        self.is_stream = data.get("is_live")
        self.uploader = data.get("uploader")
        self.thumbnail = data.get("thumbnail")
        self.title = data.get("title")
        self.description = data.get("description")
        self.tags = data.get("tags")
        self._done = True

    async def _reload_raw_url(self):
        with ytdl.YoutubeDL(self.opts) as dl:
            f = functools.partial(dl.extract_info, self.url,
                                  download=False)

        data = await self.loop.run_in_executor(self.executor, f)
        return data["url"]

    async def load(self):
        self.source = discord.FFmpegPCMAudio(await self._reload_raw_url())

    def read(self):
        return audioop.mul(self.source.read(), 2, self.volume)

    def cleanup(self):
        self.source.cleanup()

    def set_requester(self, requester):
        self.requester = requester
        self.request_id = requester.id


class OverlaySource(discord.AudioSource):
    def __init__(self, source, overlay, player, *, vc):
        self.source = source
        self.player = player
        self._overlay_source = overlay
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
    def __init__(self, source, overlay, player, *, vc):
        super().__init__(source, overlay, player, vc=vc)
        self._overlay_source = discord.FFmpegPCMAudio(overlay)

    def read(self):
        source_data = self.source.read()
        overlay_data = self._overlay_source.read()

        if not overlay_data:
            self.player.source = self.source
            self.vc.source = self.source
            self.cleanup()
            return source_data

        source_data = audioop.mul(source_data, 2, 0.4)
        overlay_data = audioop.mul(overlay_data, 2, 8)

        return audioop.add(source_data, overlay_data, 2)

    def cleanup(self):
        self._overlay_source.cleanup()
