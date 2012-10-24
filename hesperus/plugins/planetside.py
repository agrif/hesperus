from ..plugin import CommandPlugin
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup

class PlanetSideStatus(CommandPlugin):
    STATUS_URL = 'https://lp.soe.com/code4344.2/beta/worlds'

    @CommandPlugin.register_command(r'ps2(?:status)?')
    def ps2_status(self, chans, name, match, direct, reply):
        data = BeautifulSoup(requests.get(self.STATUS_URL).text)
        reply('PlanetSide2 Server Status: ' + \
            ', '.join('%s: %s' % (s[0].string, s[1].string) \
                for s in (tr.find_all('td') for tr in data.table.tbody.find_all('tr'))))
