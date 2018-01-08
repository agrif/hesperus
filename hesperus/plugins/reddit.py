from hesperus.plugin import CommandPlugin
from hesperus.shorturl import short_url
from hesperus.core import ConfigurationError, ET

import time
import random
import json
import requests
import re

class RedditPlugin(CommandPlugin):
    MAINURL = "https://reddit.com/r/{name}.json?count={count}"
    URLFORMAT = "https://{subreddit}.reddit.com/{id}"
    USERAGENT = "Hesperus Reddit Plugin"
    TIMEOUT = 60 * 60 * 10

    @CommandPlugin.config_types(commands = ET.Element, nsfw = bool, stickies = bool, spoilers = bool, selfposts = bool, timeout = int, count = int)
    def __init__(self, core, commands=None, nsfw=False, stickies=False, spoilers=False, selfposts=False, timeout=60*60*10, count=20):
        super(CommandPlugin, self).__init__(core)
        
        self.cache = {}
        self.nsfw = nsfw
        self.stickies = stickies
        self.spoilers = spoilers
        self.selfposts = selfposts
        self.timeout = timeout
        self.count = count

        self.commands = {}
        self.matchers = {}
        if commands == None:
            commands = []
        for el in commands:
            if not el.tag.lower() == 'command':
                raise ConfigurationError('commands must contain command tags')
            names = el.get('names', "")
            expression = el.get("re", None)
            if not names and not expression:
                raise ConfigurationError('command tags must have either a names or an re attribute')

            subreddit = el.text.strip()

            for name in names.split(','):
                self.commands[name.lower()] = subreddit
            if expression:
                self.matchers[re.compile('^(?:' + expression + ')$', re.I)] = subreddit

    def get_posts(self, name):
        now = time.time()
        cached = self.cache.get(name)
        if cached and cached.get('time', 0) + self.timeout > now:
            return cached['data']

        # not cached, fetch the data
        url = self.MAINURL.format(name=name, count=self.count)
        self.log_debug('fetching {0}'.format(url))
        try:
            results = json.loads(requests.get(url, headers={'User-Agent': self.USERAGENT}).content)
            results = results['data']['children']
        except Exception:
            # bad result!
            return self.cache.get(name, {}).get('data', [])

        self.cache[name] = dict(data=results, time=now)
        return results

    def do_command(self, name, reply):
        allposts = self.get_posts(name)

        try:
            posts = []
            for p in allposts:
                p = p['data']
                if p['over_18'] and not self.nsfw:
                    continue
                if p['spoiler'] and not self.spoilers:
                    continue
                if p['stickied'] and not self.stickies:
                    continue
                if p['is_self'] and not self.selfposts:
                    continue
                posts.append(p)

            post = random.choice(posts)
            selfurl = self.URLFORMAT.format(**post).lower()
            url = post['url']
            title = post['title']
            if post['is_self'] or post['is_video']:
                reply(u'{0}: {1}'.format(title, selfurl).encode('ascii', errors='replace'))
            else:
                reply(u'{0}: {1} <{2}>'.format(title, short_url(url), selfurl).encode('ascii', errors='replace'))
        except Exception, e:
            self.log_debug('error : {0}'.format(repr(e)))
            reply('no {0} today :('.format(name))

    @CommandPlugin.register_command(r"reddit\s+(.+)")
    def reddit(self, chans, name, match, direct, reply):
            self.do_command(match.group(1), reply)

    @CommandPlugin.register_command(r"(\S+)")
    def other_command(self, chans, name, match, direct, reply):
        cmd = match.group(1).lower()
        if cmd in self.commands:
            self.do_command(self.commands[cmd], reply)
        else:
            for reobj, name in self.matchers.iteritems():
                if reobj.match(cmd):
                    self.do_command(name, reply)
                    break
