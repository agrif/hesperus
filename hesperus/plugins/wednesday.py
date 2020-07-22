import datetime
import random

from hesperus.plugin import CommandPlugin
from ..core import ConfigurationError, ET

class MyDudesPlugin(CommandPlugin):
    @CommandPlugin.config_types(urls = ET.Element)
    def __init__(self, core, urls=None):
        super(CommandPlugin, self).__init__(core)
        
        self.urls = []

        if urls == None:
            urls = []
        for el in urls:
            if not el.tag.lower() == 'url':
                raise ConfigurationError('urls must contain url tags')

            text = el.text.strip()
            self.urls.append(text)

    @CommandPlugin.register_command("wednesday")
    def wed_command(self, chans, name, match, direct, reply):
        if datetime.datetime.today().weekday() != 2:
            reply("No.")
        else:
            text = random.choice(self.urls)
            reply(text)
