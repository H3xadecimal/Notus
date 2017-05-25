from urllib import parse
import json
import functools

import youtube_dl
import aiohttp

from . import music_sources as sources

YT_PL_URL = ("https://www.googleapis.com/youtube/v3/playlistItems"
             "?part=snippet&playlistId={id}&key={key}&maxResults=50")

YT_PL_PAGE_URL = YT_PL_URL + "&pageToken={page}"

SC_PL_URL = "https://api.soundcloud.com/resolve?url={url}&client_id={key}"

OSU_SET_URL = "https://osu.ppy.sh/api/get_beatmaps?k={key}&s={id}"
OSU_MAP_URL = "https://osu.ppy.sh/api/get_beatmaps?k={key}&b={id}"

with open("config.json") as f:
    config = json.load(f)
    YT_KEY = config.get("YT_KEY", None)
    SC_KEY = config.get("SC_KEY", None)
    OSU_KEY = config.get("OSU_KEY", None)


async def get_song_info(loop, url):
    song = sources.YTDLSource(url, loop=loop)
    await song.load_data()
    return song


async def _get_playlist(id):
    async with aiohttp.ClientSession() as ses:
        async with ses.get(YT_PL_URL.format(id=id, key=YT_KEY)) as res:
            return await res.json()


async def _get_playlist_page(id, page):
    async with aiohttp.ClientSession() as ses:
        async with ses.get(YT_PL_PAGE_URL.format(id=id, key=YT_KEY,
                                                 page=page)) as res:
            return await res.json()


async def youtube_playlist(url, requester, loop=None):
    print("Iterating over youtube playlist:", url)
    id = parse.parse_qs(
            parse.splitquery(
                    url)[1]
        )["list"][0]
    jsonvar = await _get_playlist(id)
    songs = []
    for item in jsonvar["items"]:
        if ("Deleted" not in item["snippet"]["title"] and
                "Private" not in item["snippet"]["title"]):

            song = await get_song_info(
                    loop, item["snippet"]['resourceId']['videoId'])

            if song is None or song.duration is None:
                continue
            songs.append(song)

    while jsonvar.get('nextPageToken') is not None:
        jsonvar = await _get_playlist_page(id, jsonvar['nextPageToken'])

        try:
            for item in jsonvar["items"]:
                if ("Deleted" not in item["snippet"]["title"] and
                        "Private" not in item["snippet"]["title"]):

                    song = await get_song_info(
                            loop, item["snippet"]['resourceId']['videoId'])

                    if song is None or song.duration is None:
                        continue
                    songs.append(song)
        except Exception as e:
            print(jsonvar)
            print(e)

    print("Found", len(songs), "items.")
    for song in songs:
        song.set_requester(requester)
    return songs


async def soundcloud_playlist(url, requester, loop=None):
    print("Iterating over soundcloud playlist:", url)
    async with aiohttp.ClientSession() as ses:
        async with ses.get(SC_PL_URL.format(url=url, key=SC_KEY)) as res:
            data = await res.json()

    songs = []

    for item in data["tracks"]:
        song = await get_song_info(
            loop, item["permalink_url"])
        if song is None:
            continue

        songs.append(song)

    print("Found", len(songs), "items.")
    for song in songs:
        song.set_requester(requester)

    return songs


async def bandcamp_playlist(url, requester, loop):
    print("Iterating over bandcamp album:", url)
    with youtube_dl.YoutubeDL({"quiet": True}) as dl:
        f = functools.partial(dl.extract_info, url, download=False)
    res = await loop.run_in_executor(None, f)

    songs = []
    for item in res["entries"]:
        song = await get_song_info(
            loop, item['webpage_url'])
        if song is None:
            continue

        songs.append(song)

    print("Found", len(songs), "items.")
    for song in songs:
        song.set_requester(requester)

    return songs


async def osu_song(url, requester, loop):
    if "ppy.sh/b/" in url:
        url = OSU_MAP_URL

    elif "ppy.sh/s/" in url:
        url = OSU_SET_URL

    id = url.split("/")[-1]

    async with aiohttp.ClientSession() as ses:
        async with ses.get(url.format(key=OSU_KEY, id=id)) as res:
            data = await res.json()

    song = "{} - {}".format(data["artist"], data["title"])
    data = await get_song_info(loop, song)
    data.set_requester(requester)
    return data
