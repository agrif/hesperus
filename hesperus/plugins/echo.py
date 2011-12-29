from hesperus.plugin import CommandPlugin
from ..core import ConfigurationError, ET
from ..shorturl import short_url

class EchoPlugin(CommandPlugin):
    @CommandPlugin.config_types(commands = ET.Element)
    def __init__(self, core, commands=None):
        super(CommandPlugin, self).__init__(core)
        
        self.commands = {}
        
        if commands == None:
            commands = []
        for el in commands:
            if not el.tag.lower() == 'command':
                raise ConfigurationError('commands must contain command tags')
            names = el.get('names', None)
            if names == None:
                raise ConfigurationError('command tags must have a names attribute')
            text = el.text.strip()
            
            for name in names.split(","):
                self.commands[name.lower()] = text
        
    @CommandPlugin.register_command(r"(\S+)")
    def echo_command(self, chans, name, match, direct, reply):
        cmd = match.group(1).lower()
        if not cmd in self.commands:
            return
        reply("%s" % (self.commands[cmd],))
