from hesperus.plugin import CommandPlugin
from hesperus.shorturl import short_url
import urllib

class GooglePlugin(CommandPlugin):
    @CommandPlugin.register_command(r"google\s+(.+)")
    def list_command(self, chans, name, match, direct, reply):
        enc_query = urllib.quote_plus(match.group(1))
        url = short_url("http://www.google.com/search?q=" + enc_query)
        reply('"%s": %s' % (match.group(1), url))
