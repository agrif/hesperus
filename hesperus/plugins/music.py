from ..plugin import CommandPlugin

import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup

class IcecastStatus(CommandPlugin):
    @CommandPlugin.config_types(icecast_url=str)
    def __init__(self, core, icecast_url):
        super(IcecastStatus, self).__init__(core)
        self._url = icecast_url

    @CommandPlugin.register_command(r'radio')
    def radio_status_command(self, chans, name, match, direct, reply):
        for stream in self._get_status():
            reply('{title} [{listeners}]: {song}'.format(
                title=stream['Stream Title'],
                listeners=stream['Current Listeners'],
                song=self._remove_unicode(stream['Current Song'])))

    def _get_status(self):
        page = BeautifulSoup(requests.get(self._url).content)
        streams = []
        for div in page.findAll('div', attrs={'class': 'streamheader'}):
            table = div.nextSibling.nextSibling
            streams.append(dict((tr.td.string, tr.td.nextSibling.nextSibling.string) \
                for tr in table.findAll('tr')))
        return streams

    def _remove_unicode(self, ustr):
        return ''.join(c if ord(c) < 127 else '?' for c in ustr)
