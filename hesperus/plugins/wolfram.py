import sys
from urllib import urlencode
from urllib2 import urlopen
from xml.etree import ElementTree

from hesperus.plugin import CommandPlugin
from hesperus.shorturl import short_url

alpha_api_url = "http://api.wolframalpha.com/v2/query"
alpha_web_url = "http://www.wolframalpha.com/input/"

def alpha(s, alpha_app_id):
    args = {}
    args['appid'] = alpha_app_id
    args['input'] = s
    args['format'] = 'plaintext'
    args['podindex'] = "1,2"
    
    url = alpha_api_url + "?" + urlencode(args)
    web_url = alpha_web_url + "?" + urlencode({'i' : s})
    data = ElementTree.parse(urlopen(url)).getroot()
    
    if data.get('error', 'true').lower() == 'true' or data.get('success', 'false').lower() == 'false':
        return {'success' : False, 'web' : web_url, 'input' : None, 'output' : None}
    
    simple_data = []
    input_data = []
    
    for el in data.findall('pod'):
        name = el.get('id')
        for subel in el.findall('subpod'):
            textel = subel.find('plaintext')
            if textel is None or textel.text is None:
                continue
            if name == "Input":
                input_data.append(textel.text)
            else:
                simple_data.append(textel.text)
        if name != "Input":
            break
    
    ret = {}
    ret['success'] = True
    ret['web'] = web_url
    ret['input'] = '\n'.join(input_data)
    ret['output'] = '\n'.join(simple_data)
    
    if ret['output'] == '':
        ret['output'] = ret['input']
    
    return ret

class AlphaPlugin(CommandPlugin):
    @CommandPlugin.config_types(app_id=str)
    def __init__(self, core, app_id=''):
        super(AlphaPlugin, self).__init__(core)
        self.app_id = app_id
    
    @CommandPlugin.register_command(r"(?:wolframalpha|wa|alpha|=)\s+(.+)")
    def alpha_command(self, chans, match, direct, reply):
        ret = alpha(match.group(1), self.app_id)
        if not ret['success']:
            reply('wolfram alpha is confused: %s' % short_url(ret['web']))
        else:
            s = ret['output'].splitlines()
            web = short_url(ret['web'])
            if len(s) == 1:
                reply('%s (%s)' % (s[0], web))
            else:
                for part in s:
                    reply(part)
                reply('(%s)' % web)
            
