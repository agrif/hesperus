import re

from hesperus.plugin import CommandPlugin
from ..core import ConfigurationError, ET
from ..shorturl import short_url

class EchoPlugin(CommandPlugin):
    """When someone says a line of text directly to the bot, the bot will
    respond as configured.

    Does simple text or regular expression matching on the input and responds
    with a static line for output.

    Takse one configuration element: <commands>
    Each <command> element can have either a names attribute: a comma separated
    list of text to match on, or an re attribute: a regular expression to
    match. The text of the <command> element will be the response.

    """
    @CommandPlugin.config_types(commands = ET.Element)
    def __init__(self, core, commands=None):
        super(CommandPlugin, self).__init__(core)
        
        self.commands = {}
        self.matchers = {}
        
        if commands == None:
            commands = []
        for el in commands:
            if not el.tag.lower() == 'command':
                raise ConfigurationError('commands must contain command tags')
            names = el.get('names', "")
            expression = el.get("re", None)
            if not names and not expression:
                raise ConfigurationError('command tags must have either a names or an re attribute')

            text = el.text.strip()
            
            for name in names.split(","):
                self.commands[name.lower()] = text

            if expression:
                self.matchers[ re.compile(expression, re.I) ] = text
        
    @CommandPlugin.register_command(r"(\S+)")
    def echo_command(self, chans, name, match, direct, reply):
        cmd = match.group(1).lower()
        if cmd in self.commands:
            reply("%s" % (self.commands[cmd],))
        else:
            for reobj, text in self.matchers.iteritems():
                if reobj.match(cmd):
                    reply(text)
                    break
