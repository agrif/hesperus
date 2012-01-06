import time

import feedparser

from ..plugin import PollPlugin
from ..shorturl import short_url
from ..core import ET, ConfigurationError

class Feed(object):
    def __init__(self, url, formatstr):
        self.url = url
        self.formatstr = formatstr

        # Go ahead and fetch the feed so we can see what entries are already there
        feedobj = self._fetch()
        self.seen_entries = set(
                e.id for e in feedobj.entries
                )

    def _fetch(self):
        feedobj = feedparser.parse(self.url)
        return feedobj

    def _format_entry(self, feed, entry):
        return self.formatstr.format(f=feed, e=entry) + short_url(entry['link'])

    def get_new_events(self):
        """Returns an iterator over formatted strings for any new entries to
        this feed

        """
        feedobj = self._fetch()

        for entry in feedobj.entries:
            if entry.id not in self.seen_entries:
                self.seen_entries.add(entry.id)
                yield self._format_entry(feedobj.feed, entry)

    def __str__(self):
        return "<Feed for %s in channels %r>" % (self.url, self.channels)

class RSSWatcher(PollPlugin):
    """A generic RSS / Atom feed watcher. This uses the python feedparser library (pip install feedparser)

    Since every feed is slightly different, each feed takes a format string to
    determine what string is sent to parent.send_outgoing(). This format string
    is parsed by the standard Python .format() method of strings. It is passed
    two objects:
        e - the FeedParserDict object for the particular entry
        f - the FeedParserDict object for the feed.

    See http://packages.python.org/feedparser/reference.html for what
    information can be retrieved from these objects.

    Example format string:
        New Slashdot post: "{e[title]}" by {e[author]} 

    The entry is formatted according to that format string. A shortened url
    from e['link'] is automatically appended to the end. The above will get formatted into e.g.

        New Slashdot post: "Thick Dust Alters NASA Mars Rover Plans" by samzenpus http://goo.gl/DV2Ir

    Here is an example xml snippet for configuring this plugin:
    <plugin type="hesperus.plugins.rsswatcher.RSSWatcher" channels="default">
        <feeds>
            <feed>
                <channel>default</channel>
                <channel>other</channel>
                <url>http://rss.slashdot.org/Slashdot/slashdot</url>
                <format>New Slashdot post: "{e[title]}" by {e[author]} </format>
            </feed>
        </feeds>
    </plugin>

    """
    poll_interval = 60
    ratelimit = 5

    @PollPlugin.config_types(feeds=ET.Element)
    def __init__(self, core, feeds):
        super(RSSWatcher, self).__init__(core)

        self.last_msg = 0

        self.feeds = []

        if feeds == None:
            feeds = []
        for feedel in feeds:
            if not feedel.tag.lower() == 'feed':
                raise ConfigurationError('feeds must contain feed tags')

            channels = []
            for el in feedel:
                tagname = el.tag.lower()
                if tagname == "channel":
                    channels.append(el.text)
                elif tagname == "url":
                    url = el.text
                elif tagname == "format":
                    formatstr = el.text

            self.feeds.append(
                    (Feed(url, formatstr), channels)
                    )

    def poll(self):
        for feedobj, channels in self.feeds:
            for responsestr in feedobj.get_new_events():
                for chan in channels:
                    while time.time() < self.last_msg + self.ratelimit:
                        yield
                    self.parent.send_outgoing(chan, responsestr)
                    self.last_msg = time.time()
                    yield
                yield
            yield
