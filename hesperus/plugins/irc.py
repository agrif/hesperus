from ircbot import SingleServerIRCBot as IRCBot
from irclib import nm_to_n, irc_lower
from ..core import ConfigurationError, ET
from ..plugin import Plugin
import re
import string

class IRCPluginBot(IRCBot):
    def __init__(self, plugin, channels):
        IRCBot.__init__(self, [(plugin.server, plugin.port)], plugin.nick, plugin.nick)
        self.initial_channels = channels
        self.plugin = plugin
    
    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")
    
    def on_welcome(self, c, e):
        self.plugin.log_message("connected to", self.plugin.server)
        if self.plugin.nickserv_password:
            self.plugin.log_verbose("sending password to NickServ...")
            self.connection.privmsg("NickServ", "identify " + self.plugin.nickserv_password)
        for chan in self.initial_channels:
            c.join(chan)
    
    def strip_nonprintable(self, s):
        return filter(lambda c: c in string.printable, s)
    
    def on_privmsg(self, c, e):
        source = nm_to_n(e.source())
        msg = e.arguments()[0].strip()
        msg = self.strip_nonprintable(msg)
        self.do_command(source, None, msg)
        
    def on_pubmsg(self, c, e):
        channel = e.target()
        source = nm_to_n(e.source())
        msg = e.arguments()[0].strip()
        msg = self.strip_nonprintable(msg)
        def reply(msg):
            self.connection.privmsg(channel, msg)
        self.plugin.do_input([channel], source, msg, False, reply)
    
    def do_command(self, source, channel, cmd):
        if cmd == "":
            return
        
        def reply(msg):
            if channel == None:
                self.connection.privmsg(source, msg)
            else:
                self.connection.privmsg(channel, "%s: %s" % (source, msg))
        
        channels = []
        if channel != None:
            channels.append(channel)
        else:
            for chan in self.channels:
                if self.channels[chan].has_user(source):
                    channels.append(chan)
        self.plugin.do_input(channels, source, cmd, True, reply)

class IRCPlugin(Plugin):
    @Plugin.config_types(server=str, port=int, nick=str, nickserv_password=str, channelmap=ET.Element, nickmap=ET.Element, inline_commands=bool, alternate_nicks=ET.Element, command_chars=str)
    def __init__(self, core, server='irc.freenode.net', port=6667, nick='hesperus', nickserv_password=None, channelmap=None, nickmap=None, inline_commands=False, alternate_nicks=None, command_chars="", name_sep_chars=",:"):
        super(IRCPlugin, self).__init__(core, daemon=True)
        
        self.server = server
        self.port = port
        self.nick = nick
        self.nickserv_password = nickserv_password
        self.chanmap = {}
        self.nickmap = {}
        self.inline_commands = inline_commands
        self.nicknames = [nick]
        
        if alternate_nicks == None:
            alternate_nicks = []
        for el in alternate_nicks:
            if not el.tag.lower() == 'nick':
                raise ConfigurationError('alternate-nicks must contain nick tags')
            self.nicknames.append(el.text.strip())
        self.nicknames = map(lambda s: s.lower(), self.nicknames)
        
        if channelmap == None:
            channelmap = []
        for el in channelmap:
            if not el.tag.lower() == 'channel':
                raise ConfigurationError('channelmap must contain channel tags')
            channel = el.get('name', None)
            irc_channel = el.text
            if not channel or not irc_channel:
                raise ConfigurationError('invalid channel tag')
            
            if not channel in self.chanmap:
                self.chanmap[channel] = [irc_channel]
            else:
                self.chanmap[channel].append(irc_channel)
        
        if nickmap == None:
            nickmap = []
        for el in nickmap:
            if not el.tag.lower() == 'nick':
                raise ConfigurationError('nickmap must contain nick tags')
            channel = el.get('channel', None)
            irc_nick = el.text
            if not channel or not irc_nick:
                raise ConfigurationError('invalid nick tag')
            
            if not channel in self.nickmap:
                self.nickmap[channel] = [irc_nick]
            else:
                self.nickmap[channel].append(irc_nick)
        
        channels = []
        for k in self.chanmap:
            self.subscribe(k)
            for chan in self.chanmap[k]:
                if not chan in channels:
                    channels.append(chan)
        for k in self.nickmap:
            self.subscribe(k)
        
        # create a command-matching re
        re_chars = "|".join(map(re.escape, command_chars))
        re_names = "|".join(map(re.escape, self.nicknames))
        re_names_sep = "|".join(map(re.escape, name_sep_chars))
        self.command_re = r"(?:%s)\s*(?:%s)\s*" % (re_names, re_names_sep)
        if len(re_chars) > 0:
            self.command_re = "(?:%s|%s)" % (self.command_re, re_chars)
        self.command_re += "(.*)"
        
        self.bot = IRCPluginBot(self, channels)
        
    def run(self):
        self.log_verbose("connecting...")
        self.bot.start()
    
    # FIXME stop properly -- might need a different irc lib
    #def stop(self):
    #    super(IRCPlugin, self).stop()
    
    def do_input(self, irc_channels, irc_nick, msg, direct, reply):
        chans = []
        for irc_channel in irc_channels:
            for k in self.chanmap:
                if irc_channel in self.chanmap[k] and not k in chans:
                    chans.append(k)
        for k in self.nickmap:
            if irc_nick in self.nickmap[k] and not k in chans:
                chans.append(k)
        
        # some indirect messages may actually be direct, or have
        # embedded direct messages
        if not direct:
            direct_re = "^" + self.command_re + "$"
            whole = re.match(direct_re, msg, re.IGNORECASE)
            old_reply = reply
            if whole:
                direct = True
                msg = whole.group(1)
                reply = lambda s: old_reply(irc_nick + ": " + s)
            elif self.inline_commands:
                part = re.search("(?:\(|\[)" + self.command_re + "(?:\)|\])", msg, re.IGNORECASE)
                if part:
                    part_msg = part.group(1)
                    part_reply = lambda s: old_reply(irc_nick + ": " + s)
                    self.parent.handle_incoming(chans, part_msg, True, part_reply)
        
        self.parent.handle_incoming(chans, msg, direct, reply)
    
    def send_outgoing(self, chan, msg):
        if chan in self.chanmap:
            for irc_chan in self.chanmap[chan]:
                self.bot.connection.notice(irc_chan, msg)
        if chan in self.nickmap:
            for irc_nick in self.nickmap[chan]:
                self.bot.connection.notice(irc_nick, msg)
