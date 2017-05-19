import shutil
import aiohttp
import requests

try:
    from urlparse import urlunsplit
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlunsplit, urlencode


def find_executable(executable):
    '''
    Finds executable in PATH
    Returns:
        string or None
    '''
    return shutil.which(executable)


def process_options(valid_options, _options, error=Exception):
    unknown_options = set(_options.keys()).difference(valid_options.keys())
    if unknown_options:
        raise error('Unknown options: %s' % ', '.join(unknown_options))

    options = dict((key, _options.get(key, val.get('default', None)))
                   for key, val in valid_options.items())
    for option in options.keys():
        val = options[option]
        data = valid_options[option]
        typ = data['type']
        if typ not in ['int', 'float', 'str', 'enum', 'bool', 'exec']:
            raise error('Bad type: %s for option %s' % (typ, option),
                        ['int', 'float', 'str', 'enum', 'bool'])
        keys = data.keys()
        if typ == 'int':
            val = int(float(val))
        if typ == 'float':
            val = float(val)
        if typ in ['int', 'float']:
            if 'min' in keys:
                if val < data['min']:
                    raise error('Bad %s: %s' % (option, val),
                                'Min is %s' % data['min'])
            if 'max' in keys:
                if val > data['max']:
                    raise error('Bad %s: %s' % (option, val),
                                'Max is %s' % data['max'])
        if typ == 'enum':
            if val not in data['values']:
                raise error('Bad %s value: %s' % (option, val), data['values'])
        if typ == 'bool':
            val = (True if str(val).lower() in ['y', '1', 'yes', 'true', 't']
                   else False)
        if typ == 'exec':
            if isinstance(val, list):
                vals = val
                for val in vals:
                    val = find_executable(val)
                    if val:
                        break
            else:
                val = find_executable(val)
        options[option] = val
    return options


class MaryTTS:
    def __init__(self, **_options):
        self.ioptions = process_options(self.__class__.get_init_options(),
                                        _options)

        # Pre-caching potentially slow results
        self.default_language = 'en'
        self.languages_options = {}
        self.default_options = {}
        self.optionspec = {}
        self.languages = self._get_languages()
        self.configure_default()

    def configure_default(self, **_options):
        '''
        Sets default configuration.
        Raises TTSError on error.
        '''
        language, voice, voiceinfo, options = self._configure(**_options)
        self.languages_options[language] = (voice, options)
        self.default_language = language
        self.default_options = options

    @classmethod
    def get_init_options(cls):
        return {
            'enabled': {
                'description': 'Is enabled?',
                'type': 'bool',
                'default': False,
            },
            'scheme': {
                'description': 'HTTP schema',
                'type': 'enum',
                'default': 'http',
                'values': ['http', 'https'],
            },
            'host': {
                'description': 'Mary server address',
                'type': 'str',
                'default': '127.0.0.1',
            },
            'port': {
                'description': 'Mary server port',
                'type': 'int',
                'default': 59125,
                'min': 1,
                'max': 65535,
            }
        }

    def _get_languages(self):
        res = requests.get(self._makeurl('voices'), timeout=5).text
        langs = {}
        for voice in [row.split() for row in res.split('\n') if row]:
            lang = voice[1].split('_')[0]
            langs.setdefault(lang, {'default': voice[0], 'voices': {}})
            langs[lang]['voices'][voice[0]] = {
                'gender': voice[2],
                'locale': voice[1]
            }
        return langs

    def _configure(self, language=None, voice=None, **_options):
        language = language or "en"
        lang_voice, lang_options = self._get_language_options(language)
        voice = voice or lang_voice

        if language not in self.languages.keys():
            raise Exception('Bad language: %s' % language,
                            self.languages.keys())

        voice = voice if voice else self.languages[language]['default']
        if voice not in self.languages[language]['voices'].keys():
            raise Exception('Bad voice: %s' % voice,
                            self.languages[language]['voices'].keys())
        voiceinfo = self.languages[language]['voices'][voice]

        lang_options.update(_options)
        options = process_options(self.optionspec, lang_options)
        return language, voice, voiceinfo, options

    def _makeurl(self, path, query={}):
        query_s = urlencode(query)
        urlparts = (self.ioptions['scheme'], self.ioptions['host'] + ':' +
                    str(self.ioptions['port']), path, query_s, '')
        return urlunsplit(urlparts)

    def _get_language_options(self, language):
        if language in self.languages_options.keys():
            return self.languages_options[language]
        return None, {}

    async def _say(self, phrase, **_options):
        language, voice, voiceinfo, options = self._configure(**_options)
        query = {'OUTPUT_TYPE': 'AUDIO',
                 'AUDIO': 'WAVE_FILE',
                 'INPUT_TYPE': 'TEXT',
                 'INPUT_TEXT': phrase,
                 'LOCALE': voiceinfo['locale'],
                 'VOICE': voice}

        async with aiohttp.ClientSession() as ses:
            async with ses.get(self._makeurl('/process', query=query)) as res:
                return await res.read()
