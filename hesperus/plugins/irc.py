from ircbot import SingleServerIRCBot as IRCBot
from irclib import nm_to_n, irc_lower
from ..core import ConfigurationError, ET
from ..plugin import Plugin

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
            self.privmsg("NickServ", "identify " + self.plugin.nickserv_password)
        for chan in self.initial_channels:
            c.join(chan)
    
    def on_privmsg(self, c, e):
        source = nm_to_n(e.source())
        self.do_command(source, None, e.arguments()[0].strip())
        
    def on_pubmsg(self, c, e):
        a = e.arguments()[0].split(":", 1)
        b = e.arguments()[0].split(",", 1)
        channel = e.target()
        source = nm_to_n(e.source())
        if len(a) > 1 and irc_lower(a[0].strip()) == irc_lower(self.connection.get_nickname()):
            self.do_command(source, channel, a[1].strip())
        elif len(b) > 1 and irc_lower(b[0].strip()) == irc_lower(self.connection.get_nickname()):
            self.do_command(source, channel, b[1].strip())
        else:
            def reply(msg):
                self.connection.privmsg(channel, msg)
            self.plugin.do_input([channel], e.arguments()[0].strip(), False, reply)
    
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
        self.plugin.do_input(channels, cmd, True, reply)

class IRCPlugin(Plugin):
    @Plugin.config_types(server=str, port=int, nick=str, nickserv_password=str, channelmap=ET.Element)
    def __init__(self, core, server='irc.freenode.net', port=6667, nick='hesperus', nickserv_password=None, channelmap=None):
        super(IRCPlugin, self).__init__(core, daemon=True)
        
        self.server = server
        self.port = port
        self.nick = nick
        self.nickserv_password = nickserv_password
        self.chanmap = {}

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
        
        channels = []
        for k in self.chanmap:
            for chan in self.chanmap[k]:
                if not chan in channels:
                    channels.append(chan)
        self.bot = IRCPluginBot(self, channels)
        
    def run(self):
        self.log_verbose("connecting...")
        self.bot.start()
    
    # FIXME stop properly -- might need a different irc lib
    #def stop(self):
    #    super(IRCPlugin, self).stop()
    
    def do_input(self, irc_channels, msg, direct, reply):
        chans = []
        for irc_channel in irc_channels:
            for k in self.chanmap:
                if irc_channel in self.chanmap[k] and not k in chans:
                    chans.append(k)
        self.parent.handle_incoming(chans, msg, direct, reply)
