import urllib, urllib2
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hesperus.shorturl')

try:
    with open('google-api-key.conf') as f:
        logger.debug('Loading google API key...')
        google_api_key = f.read().strip()
except Exception as err:
    logger.warning('Failed to load google API key: %s', err)
    logger.exception(err)
    google_api_key=''
logger.debug('Using google API key: %s', google_api_key)

providers = {}
def provider(name):
    def inner_provider(func):
        global providers
        providers[name] = func
        return func
    return inner_provider

@provider("goo.gl")
def short_url_goo_gl(url):
    global google_api_key
    if not url:
        return None
    
    apiurl = 'https://www.googleapis.com/urlshortener/v1/url?key={}'.format(google_api_key)
    data = json.dumps({'longUrl' : url})
    headers = {'Content-Type' : 'application/json'}
    r = urllib2.Request(apiurl, data, headers)
    
    try:
        retdata = urllib2.urlopen(r).read()
        retdata = json.loads(retdata)
        return retdata.get('id', url)
    except urllib2.URLError as err:
        logging.warning('Got error from url shortener: %s', err)
        return url
    except ValueError:
        return url

@provider("git.io")
def short_url_git_io(url):
    if not url:
        return None
    
    apiurl = 'http://git.io'
    data = urllib.urlencode({'url' : url})
    r = urllib2.Request(apiurl, data)
    
    try:
        retdata = urllib2.urlopen(r)
        if retdata.code == 201:
            return retdata.headers['location']
        else:
            return url
    except urllib2.URLError:
        return url
    except ValueError:
        return url

def short_url(url, provider="goo.gl"):
    global providers
    try:
        return providers[provider](url)
    except KeyError:
        return url
