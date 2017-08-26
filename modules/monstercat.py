from utils.command_system import group
import urllib.parse as urls
import discord
import re

BASE_URI = 'https://connect.monstercat.com/api'


def get_name(url: str) -> str:
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
    else:
        return url


class Monstercat:
    def __init__(self, amethyst):
        self.amethyst = amethyst

    @group()
    async def search(self, ctx):
        '''Search for various Monstercat things.'''
        await self.amethyst.send_command_help(ctx)

    @search.command(usage='<artist>')
    async def artist(self, ctx):
        '''Search for an artist.'''
        if not ctx.args:
            return await ctx.send('Please give me an artist to search for.')

        async with ctx.typing():
            artist = urls.quote(ctx.suffix.lower().replace(' & ', '-').replace(' ', '-'))
            url = BASE_URI + f'/catalog/artist/{artist}'

            async with self.amethyst.session.get(url) as r:
                if 200 <= r.status < 300:
                    res = await r.json()
                else:
                    return await ctx.send(f'Invalid response code: `{r.status}`')

            if 'error' in res and res['message'] != 'Artist not found.':
                return await ctx.send(f'Error: {res.message}')
            elif 'error' in res:
                url = BASE_URI + f"/catalog/artist?fuzzy=name,{urls.quote(ctx.suffix.split(' ')[0])}"

                async with self.amethyst.session.get(url) as r:
                    if 200 <= r.status < 300:
                        res = await r.json()
                    else:
                        return await ctx.send(f'Invalid response code: `{r.status}`')

                if not res['results']:
                    return await ctx.send('Artist not found.')
                else:
                    res = res['results'][0]

            url = BASE_URI + f"/catalog/artist/{res['vanityUri']}/releases"

            async with self.amethyst.session.get(url) as r:
                if 200 <= r.status < 300:
                    releases = await r.json()
                else:
                    return await ctx.send(f'Invalid response code: `{r.status}`')

        description = discord.Embed.Empty

        if 'about' in res:
            description = res['about']

        embed = discord.Embed(title=res['name'], description=description)
        years = ', '.join(str(x) for x in sorted(res['years']))

        embed.set_thumbnail(url=res['profileImageUrl'])
        embed.set_footer(text=f'Release years: {years}')

        if 'bookings' in res:
            embed.add_field(name='Bookings', value=res['bookings'].replace('Booking: ', ''), inline=False)

        if 'managementDetail' in res:
            embed.add_field(name='Management', value=res['managementDetail'].replace('Management: ', ''), inline=False)

        embed.add_field(name='Social Media', value=' '.join(f'**__[{get_name(x)}]({x})__**' for x in res['urls']),
                        inline=False)
        embed.add_field(name='Releases', value=releases['total'], inline=False)

        await ctx.send(embed=embed)


def setup(amethyst):
    return Monstercat(amethyst)
