from utils.command_system import command, group
from typing import Union
from datetime import datetime
import urllib.parse as urls
import discord
import re

BASE_URI = 'https://connect.monstercat.com/api'


def get_name(url: str) -> str:
    """Returns the formatted name for social media link."""
    if re.search(r'^(?:https?://)?(?:www\.)?facebook\.com', url):
        return 'Facebook'
    elif re.search(r'^(?:https?://)?(?:www\.)?soundcloud\.com', url):
        return 'SoundCloud'
    elif re.search(r'^(?:https?://)?(?:www\.)?instagram\.com', url):
        return 'Instagram'
    elif re.search(r'^(?:https?://)?(?:www\.)?youtube\.com', url):
        return 'YouTube'
    elif re.search(r'^(?:https?://)?(?:www\.)?twitter\.com', url):
        return 'Twitter'
    elif re.search(r'^(?:https?://)?open\.spotify\.com', url):
        return 'Spotify'
    elif re.search(r'^(?:https?://)?(?:www\.)?beatport\.com', url):
        return 'Beatport'
    elif re.search(r'^(?:https?://)?itunes\.apple\.com', url):
        return 'iTunes'
    elif re.search(r'^(?:https?://)?(?:www\.)?mixcloud\.com', url):
        return 'Mixcloud'
    elif re.search(r'^(?:https?://)?music\.monstercat\.com', url):
        return 'Bandcamp'
    else:
        return url


def is_catalog_id(id: str) -> bool:
    """Checks if a given string matches a catalog ID."""
    if (re.search(r'^MCUV-\d+', id) or  # Uncaged Albums
            re.search(r'^MCEP\d{3}$', id) or  # EPs
            re.search(r'^MCF\d{3}$', id) or  # Free Downloads
            re.search(r'^COTW\d{3}$', id) or  # Call of the Wild
            re.search(r'^MCP\d{3}$', id) or  # Monstercat Podcast (pre-COTW)
            re.search(r'^MCS\d{3}$', id) or  # Single
            re.search(r'^MCLP\d{3}$', id) or  # Long Play
            re.search(r'^MCRL\d{3}$', id) or  # Rocket League Album
            re.search(r'^MC\d{3}$', id) or  # Album (pre-Uncaged)
            re.search(r'^MCB\d{3}$', id) or  # Best of Compilations
            re.search(r'^MCX\d{3}(?:-\d)$', id)):  # Special Compilations
        return True
    else:
        return False


def get_type_from_catalog_id(id: str) -> Union[str, None]:
    """Gets the type of a release from its catalog ID."""
    if re.search(r'^MCUV-\d+$', id) or re.search(r'^MC\d{3}$', id):
        return 'Album'
    elif re.search(r'^MCB\d{3}$', id):
        return 'Best of Compilation'
    elif re.search(r'^MCX\d{3}$', id):
        return 'Special Compilation'
    elif re.search(r'^MCX\d{3}-\d$', id):
        return '5 Year Anniversary Track'
    elif re.search(r'^COTW\d{3}$', id):
        return 'Call of the Wild'
    elif re.search(r'^MCP\d{3}$', id):
        return 'Podcast'
    elif re.search(r'^MCRL\d{3}$', id):
        return 'Rocket League Album'
    elif re.search(r'^MCLP\d{3}$', id):
        return 'Long Play'
    elif re.search(r'^MCEP\d{3}$', id):
        return 'Extended Play'
    elif re.search(r'^MCF\d{3}$', id):
        return 'Free Download'
    elif re.search(r'^MCS\d{3}$', id):
        return 'Single'
    else:
        return None


def gen_duration(seconds: int) -> str:
    """Generate a human readable time from seconds."""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return f'{hours:02}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'


class Monstercat:
    def __init__(self, amethyst):
        self.amethyst = amethyst

    @command(aliases=['ids', 'catalogid', 'catalogids'])
    async def catalog(self, ctx):
        """Explains Monstercat catalog IDs, and what they mean."""
        await ctx.send('Monstercat has a set of different catalog IDs which are used to differentiate types of '
                       'releases, and when they were released in relation to each other.\n\n'
                       '**List of (Known) Catalog IDs**\n'
                       '*Any instances of `X`, with the exception of `MCX` are meant to be a number.*\n\n'
                       '**MCUV-X** - Uncaged Albums\n'
                       '**MCXXX** - Albums before Uncaged\n'
                       '**MCBXXX** - Best of Compilations\n'
                       '**MCXNNN** - "Special" Compilations\n'
                       '**MCX-N** - 5 Year Anniversary Track\n'
                       '**MCRLXXX** - Rocket Leage Album\n'
                       '**MCLPXXX** - Long Play (LP)\n'
                       '**MCEPXXX** - Extended Play (EP)\n'
                       '**COTWXXX** - Call of the Wild\n'
                       '**MCPXXX** - Monstercat Podcast (before the rename to Call of the Wild)\n'
                       '**MCSXXX** - Single\n'
                       '**MCFXXX** - Free Download')

    @group()
    async def search(self, ctx):
        """Search for various Monstercat things."""
        await self.amethyst.send_command_help(ctx)

    @search.command(usage='<artist>')
    async def artist(self, ctx):
        """Search for an artist."""
        if not ctx.args:
            return await ctx.send('Please give me an artist to search for.')

        async with ctx.typing():
            # Request data for artist, with a fallback in case it can't be found directly

            artist = urls.quote(ctx.suffix.lower().replace(' & ', '-').replace(' ', '-'))
            url = BASE_URI + f'/catalog/artist/{artist}'

            async with self.amethyst.session.get(url) as r:
                if 200 <= r.status < 300:
                    data = await r.json()
                else:
                    return await ctx.send(f'Invalid response code: `{r.status}`')

            if 'error' in data and data['message'] != 'Artist not found.':
                return await ctx.send(f'Error: {data.message}')
            elif 'error' in data:
                url = BASE_URI + f"/catalog/artist?fuzzy=name,{urls.quote(ctx.suffix.split(' ')[0])}"

                async with self.amethyst.session.get(url) as r:
                    if 200 <= r.status < 300:
                        data = await r.json()
                    else:
                        return await ctx.send(f'Invalid response code: `{r.status}`')

                if not data['results']:
                    return await ctx.send('Artist not found.')
                else:
                    data = data['results'][0]

            url = BASE_URI + f"/catalog/artist/{data['vanityUri']}/releases"

            async with self.amethyst.session.get(url) as r:
                if 200 <= r.status < 300:
                    releases = await r.json()
                else:
                    return await ctx.send(f'Invalid response code: `{r.status}`')

        # Construct embed from data
        # Any errors relating to getting valid data shouldn't happen here
        # If they do, please open an issue (you should regardless)

        description = discord.Embed.Empty

        if 'about' in data:
            description = data['about']

        embed = discord.Embed(title=data['name'], description=description)
        years = ', '.join(str(x) for x in sorted(y for y in data['years'] if y is not None))

        embed.set_thumbnail(url=data['profileImageUrl'])
        embed.set_footer(text=f'Release years: {years}')

        if 'bookings' in data:
            embed.add_field(name='Bookings', value=data['bookings'].replace('Booking: ', ''), inline=False)

        if 'managementDetail' in data:
            embed.add_field(name='Management', value=data['managementDetail'].replace('Management: ', ''), inline=False)

        embed.add_field(name='Social Media', value=' '.join(f'**__[{get_name(x)}]({x})__**' for x in data['urls']),
                        inline=False)
        embed.add_field(name='Releases', value=releases['total'], inline=False)

        await ctx.send(embed=embed)

    @search.command(aliases=['track'], usage='<track>')
    async def release(self, ctx):
        """
        Search for a release.
        You can either use the name of the release, or use its catalog ID.
        """
        if not ctx.args:
            return await ctx.send('Please give me a release to search for.')

        async with ctx.typing():
            # Get data for the release, with a fallback if its not a catalog id

            if is_catalog_id(ctx.suffix.upper()):
                url = BASE_URI + f'/catalog/release/{ctx.suffix.upper()}'

                async with self.amethyst.session.get(url) as r:
                    if 200 <= r.status < 300:
                        data = await r.json()
                    else:
                        return await ctx.send(f'Invalid response code: `{r.status}`')

                if 'error' in data and data['message'] != 'The specified resource was not found.':
                    return await ctx.send(f'Error: {data.message}')
                elif 'error' in data:
                    return await ctx.send('That release could not be found.')

                url = BASE_URI + f"/catalog/release/{data['_id']}/tracks"

                async with self.amethyst.session.get(url) as r:
                    if 200 <= r.status < 300:
                        tracks = await r.json()
                    else:
                        return await ctx.send(f'Invalid response code: `{r.status}`')
            else:
                song = urls.quote(ctx.suffix.lower())
                url = BASE_URI + f'/catalog/release?fuzzy=title,{song}'

                async with self.amethyst.session.get(url) as r:
                    if 200 <= r.status < 300:
                        data = await r.json()
                    else:
                        return await ctx.send(f'Invalid response code: `{r.status}`')

                if not data['results']:
                    return await ctx.send(f'No results found for `{ctx.suffix}`')

                data = data['results'][0]
                url = BASE_URI + f"/catalog/release/{data['_id']}/tracks"

                async with self.amethyst.session.get(url) as r:
                    if 200 <= r.status < 300:
                        tracks = await r.json()
                    else:
                        return await ctx.send(f'Invalid response code: `{r.status}`')

        title = f"{data['renderedArtists']} - {data['title']}"
        description = get_type_from_catalog_id(data['catalogId']) or data['type']
        timestamp = datetime.strptime(data['releaseDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
        links = ' '.join(f'**__[{get_name(x)}]({x})__**' for x in data['urls'])
        embed = discord.Embed(title=title, description=description, timestamp=timestamp)

        embed.set_thumbnail(url=data['coverUrl'].replace(' ', '%20'))

        if links:
            embed.add_field(name='Links', value=links, inline=False)

        if tracks['total'] > 1:
            # EP or album or something
            tracks = tracks['results']
            tracks_names = [f"{x['artistsTitle']} - {x['title']} **({gen_duration(round(x['duration']))})**" for x in
                            tracks]
            tracks_joined = '\n'.join(tracks_names)

            embed.add_field(name='Duration', value=gen_duration(round(sum(x['duration'] for x in tracks))))
            embed.add_field(name='Average BPM', value=round(sum(x['bpm'] for x in tracks) / len(tracks)))

            if len(tracks_joined) <= 1024:
                embed.add_field(name='Tracks', value=tracks_joined, inline=False)
            else:
                tracks1 = '\n'.join(tracks_names[:len(tracks_names) // 2])
                tracks2 = '\n'.join(tracks_names[len(tracks_names) // 2:])

                embed.add_field(name='Tracks - Part 1', value=tracks1, inline=False)
                embed.add_field(name='Tracks - Part 2', value=tracks2, inline=False)
        else:
            track = tracks['results'][0]

            embed.add_field(name='Duration', value=gen_duration(round(track['duration'])))
            embed.add_field(name='BPM', value=round(track['bpm']))

            if track['genres']:
                embed.add_field(name='Genre', value=track['genres'][0])

        await ctx.send(embed=embed)


def setup(amethyst):
    return Monstercat(amethyst)
