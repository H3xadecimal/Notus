from urllib import parse
import json
import functools

import youtube_dl
import aiohttp


YT_PL_URL = ("https://www.googleapis.com/youtube/v3/playlistItems"
             "?part=snippet&playlistId={id}&key={key}&maxResults=50")

YT_PL_PAGE_URL = YT_PL_URL + "&pageToken={page}"

SC_PL_URL = "https://api.soundcloud.com/resolve?url={url}&client_id={key}"

with open("config.json") as f:
    config = json.load(f)
    YT_KEY = config.get("YT_KEY", None)
    SC_KEY = config.get("SC_KEY", None)


async def get_song_info(loop, url):
    opts = {'format': 'bestaudio/best',
            'noplaylist': True,
            'audioformat': 'bestaudio/best',
            'quiet': True}

    try:
        ydl = youtube_dl.YoutubeDL(opts)
        func = functools.partial(ydl.extract_info, url, download=False)
        info = await loop.run_in_executor(None, func)
        if "entries" in info:
            info = info['entries'][0]
        song = info['title']
        url = info['webpage_url']
        data = {'url': url,
                'title': song,
                'stream': info.get("is_live"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                'raw_url': info['url']}
        if info.get('duration') is not None:
            data['duration'] = info['duration']
        return data
    except:
        return

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

            if song is None or song["duration"] is None:
                continue
            songs.append(song)

    while jsonvar.get('nextPageToken') is not None:
        jsonvar = await _get_playlist_page(id, jsonvar['nextPageToken'])

        try:
            for item in jsonvar["items"]:
                if ("Deleted" not in item.get["snippet"].get["title"] and
                        "Private" not in item.get("snippet").get("title")):

                    song = await get_song_info(
                            loop, item["snippet"]['resourceId']['videoId'])

                    if song is None or song["duration"] is None:
                        continue
                    songs.append(song)
        except:
            print(jsonvar)

    for song in songs:
        song["requester"] = requester
    return songs


async def soundcloud_playlist(url, requester, loop=None):
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

    for song in songs:
        song['requester'] = requester

    return songs


async def bandcamp_playlist(url, requester, loop):
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

    for song in songs:
        song["requester"] = requester

    return songs
