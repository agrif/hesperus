from hesperus.plugin import CommandPlugin
from hesperus.core import ConfigurationError

import random
import requests
import re


class GTAPlugin(CommandPlugin):

    @CommandPlugin.config_types(playlist = str)
    def __init__(self, core, playlist):
        super(CommandPlugin, self).__init__(core)
        
        self.playlist = playlist

    def get_video_ids(self):
        url = "https://www.youtube.com/playlist?list=%s" % self.playlist
        page_data = requests.get(url).content
        p = re.compile(r'data-video-id="([^"]+)"')
        return p.findall(page_data)
	

    def do_command(self, reply):
        try:
            ids = self.get_video_ids()
            vid = random.choice(ids)
            reply(r'https://youtu.be/{0}'.format(vid).encode('ascii', errors='replace'))
        except Exception, e:
            self.log_debug('error : {0}'.format(repr(e)))

    @CommandPlugin.register_command(r"gta")
    def reddit(self, chans, name, match, direct, reply):
            self.do_command(reply)

