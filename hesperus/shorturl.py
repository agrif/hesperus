import urllib2, json

def short_url(url):
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
