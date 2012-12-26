from ..plugin import CommandPlugin
import requests
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup

class PlanetSideStatus(CommandPlugin):
    STATUS_URL = 'https://lp.soe.com/ps2/live/worlds'

    @CommandPlugin.register_command(r'ps2(?:status)?\s*(.*)')
    def ps2_status(self, chans, name, match, direct, reply):
        if match.group(1):
            pattern = re.compile(match.group(1), re.I)
        else:
            pattern = re.compile('Mattherson', re.I)
        data = BeautifulSoup(requests.get(self.STATUS_URL).text)
        servers = dict((s[0].string, s[1].string) \
                for s in (tr.find_all('td') for tr in data.table.tbody.find_all('tr')))
        reply('PS2 Server Status: ' + ', '.join('%s => %s' % (sn, st) \
            for sn, st in servers.iteritems() \
            if pattern.search(sn)))
