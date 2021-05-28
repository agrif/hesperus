import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse
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
    r = urllib.request.Request(apiurl, data.encode('utf-8'), headers)
    
    try:
        retdata = urllib.request.urlopen(r).read()
        retdata = json.loads(retdata)
        return retdata.get('id', url)
    except urllib.error.URLError as err:
        logging.warning('Got error from url shortener: %s', err)
        return url
    except ValueError:
        return url

@provider("git.io")
def short_url_git_io(url):
    if not url:
        return None
    
    apiurl = 'http://git.io'
    data = urllib.parse.urlencode({'url' : url})
    r = urllib.request.Request(apiurl, data.encode('utf-8'))
    
    try:
        retdata = urllib.request.urlopen(r)
        if retdata.code == 201:
            return retdata.headers['location']
        else:
            return url
    except urllib.error.URLError:
        return url
    except ValueError:
        return url

@provider("0x0.st")
def short_url_nullptr(url):
    if not url:
        return None

    apiurl = 'http://0x0.st'
    data = urllib.parse.urlencode({'shorten' : url})
    r = urllib.request.Request(apiurl, data.encode('utf-8'))

    try:
        retdata = urllib.request.urlopen(r)
        return retdata.read().decode('utf-8').strip()
    except urllib.error.URLError:
        return url
    except ValueError:
        return url

def short_url(url, provider=None):
    global providers
    try:
        return providers[provider](url)
    except KeyError:
        return url
