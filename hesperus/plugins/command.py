import re

from ..core import ConfigurationError, ET
from ..plugin import Plugin

class CommandPlugin(Plugin):
    @Plugin.config_types(inline=bool, names=ET.Element, command_chars=str, name_sep_chars=str)
    def __init__(self, core, inline=False, names=None, command_chars="", name_sep_chars=",:"):
        super(CommandPlugin, self).__init__(core)
        
        self.inline = inline
        
        self.names = []
        if names == None:
            names = []
        for el in names:
            if not el.tag.lower() == 'name':
                raise ConfigurationError('names must contain name tags')
            self.names.append(el.text.strip().lower())
        
        # create a command-matching re
        re_chars = "|".join(map(re.escape, command_chars))
        re_names = "|".join(map(re.escape, self.names))
        re_names_sep = "|".join(map(re.escape, name_sep_chars))
        self.command_re = r"(?:%s)\s*(?:%s)\s*" % (re_names, re_names_sep)
        if len(re_chars) > 0:
            self.command_re = "(?:%s|%s)" % (self.command_re, re_chars)
        self.command_re += "(.*)"
    
    def handle_incoming(self, chans, name, msg, direct, reply):
        # skip direct messages, our work is done already
        if direct:
            return
        
        # turn indirect messages into direct messages, if appropriate
        direct_re = "^" + self.command_re + "$"
        whole = re.match(direct_re, msg, re.IGNORECASE)
        if whole:
            whole_direct = True
            whole_msg = whole.group(1)
            whole_reply = lambda s: reply(name + ": " + s)
            self.parent.handle_incoming(chans, name, whole_msg, True, whole_reply)
        elif self.inline:
            part = re.search("(?:\(|\[)" + self.command_re + "(?:\)|\])", msg, re.IGNORECASE)
            if part:
                part_msg = part.group(1)
                part_reply = lambda s: reply(name + ": " + s)
                self.parent.handle_incoming(chans, name, part_msg, True, part_reply)
