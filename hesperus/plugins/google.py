from hesperus.plugin import CommandPlugin
import urllib, urllib2, json

def _short_url(url):
    if not url:
        return None
    
    apiurl = 'https://www.googleapis.com/urlshortener/v1/url'
    data = json.dumps({'longUrl' : url})
    headers = {'Content-Type' : 'application/json'}
    r = urllib2.Request(apiurl, data, headers)
    
    try:
        retdata = urllib2.urlopen(r).read()
        retdata = json.loads(retdata)
        return retdata.get('id', url)
    except urllib2.URLError:
        return url
    except ValueError:
        return url

class GooglePlugin(CommandPlugin):
    @CommandPlugin.register_command(r"google\s+(.+)")
    def list_command(self, chans, match, direct, reply):
        enc_query = urllib.quote_plus(match.group(1))
        url = _short_url("http://www.google.com/search?q=" + enc_query)
        reply('"%s": %s' % (match.group(1), url))
