from hesperus.plugin import CommandPlugin
from hesperus.shorturl import short_url

import time
import random
import json
import requests

class BirbPlugin(CommandPlugin):
    BIRBS = "https://reddit.com/r/birbs.json?count=20"
    TIMEOUT = 60 * 60 * 10

    birbcache = None
    birbtime = None
    
    @CommandPlugin.register_command(r"bir[bd]s?")
    def birb(self, chans, name, match, direct, reply):
        self.log_debug('fetching birbs...')
        if not self.birbtime or self.birbtime + self.TIMEOUT < time.time():
            try:
                results = json.loads(requests.get(self.BIRBS, headers={'User-Agent': 'Hesperus Birb Bot'}).content)
                results = results['data']['children']
                self.birbtime = time.time()
                self.birbcache = results
            except Exception:
                results = self.birbcache
        else:
            results = self.birbcache

        if not results:
            reply("no birbs today :(")
            return

        try:
            birb = random.choice(results)['data']
            url = birb['url']
            title = birb['title']
            reply('{0}: {1}'.format(title, short_url(url)))
        except Exception:
            reply('no birbs today :((')
