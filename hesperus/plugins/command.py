import re

from ..core import ConfigurationError, ET
from ..plugin import Plugin

class CommandPlugin(Plugin):
    """Install this plugin to supplement plugins that derive from
    hesperus.plugin.CommandPlugin. This takes public (not direct) messages and
    tries to parse them in command syntax. If they match, the command is
    re-emitted as if the command were sent to the bot directly.

    """
    @Plugin.config_types(inline=bool, names=ET.Element, command_chars=str, name_sep_chars=str)
    def __init__(self, core, inline=False, names=None, command_chars="", name_sep_chars=",:"):
        """Options:

        inline
            specifies if messages are searched for commands that appear
            surrounded in parentheses somewhere in the middle of the message.
            Otherwise, only matches the exact command forms.

        names
            An ET.Element filled with names that this bot will respond to.

        name_sep_chars
            A string of characters that can act as a separator between the name
            and the command.

        command_chars
            A string of characters that may prefix a command. Good options are:
            ! or .


        In other words, the bot will respond to commands in the forms:
            name whitespace name_sep whitespace command
        or
            command_char command

        """
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
