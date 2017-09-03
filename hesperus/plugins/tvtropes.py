from hesperus.plugin import CommandPlugin
from hesperus.shorturl import short_url

import re

from googlesearch.googlesearch import GoogleSearch
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup

class TvTropesPlugin(CommandPlugin):
    QUERY = 'site:tvtropes.org %s'
    URLMATCH = re.compile(r'^https?://(?:www.)?tvtropes.org/pmwiki/pmwiki.php/([^/]+)/([^/]+)$')
    URLFORMAT = 'http://tvtropes.org/pmwiki/pmwiki.php/{0}/{1}'
    
    @CommandPlugin.register_command(r"(?:tv)?tropes?\s+(.+)")
    def trope_command(self, chans, name, match, direct, reply):
        self.log_debug('searching google for trope: ' + match.group(1))
        try:
            results = GoogleSearch().search(self.QUERY % (match.group(1),), prefetch_pages=False, prefetch_threads=1, num_results=1)
        except Exception:
            reply('trope not found :(')
            return
        if not results.results:
            reply('trope not found :(')
            return
        url = results.results[0].url
        m = self.URLMATCH.match(url)
        if not m:
            reply('trope not found :(')
            return

        subwiki = m.group(1)
        title = m.group(2)

        desc = self.get_info('Laconic', title)
        if not desc:
            desc = self.get_info(subwiki, title)

        surl = short_url(url)
        reply((desc + ' ' + surl).encode('ascii', errors='replace'))

    def get_info(self, subwiki, title):
        url = self.URLFORMAT.format(subwiki, title)
        self.log_debug('fetching url: %s' % (url,))
        page = BeautifulSoup(requests.get(url).content)
        title = page.title.string.rsplit('-', 1)[0].strip()
        if title.endswith('/ ' + subwiki):
            title = title.rsplit('/', 1)[0].strip()

        if subwiki == 'Laconic':
            descs = []
            for meta in page.findAll('meta', property='og:description'):
                c = meta['content']
                if 'inexact title' in c.lower():
                    # bad page! bad!
                    return None
                descs.append(c)
            descs.sort(key=len)
            if descs:
                return title + ': ' + descs[0]

        return title
