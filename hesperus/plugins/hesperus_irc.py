from ..core import ConfigurationError, ET
from ..plugin import Plugin
from irc.bot import SingleServerIRCBot as IRCBot
import re
import string
import time
import irc.strings

class RateLimit(object):
    """If 5 lines come in less than 2 seconds, sleep for 2 seconds"""
    def __init__(self, waittime=2):
        self.waittime = waittime
        self.lastmsg = 0
        # Number of messages that have come in since lastmsg
        self.msgcount = 0

    def call(self):
        now = time.time()
        if now - self.lastmsg > self.waittime:
            # Nothing received in waittime seconds. No delay.
            self.lastmsg = now
            self.msgcount = 0

        else:
            # received this message within the last waittime seconds of lastmsg
            self.msgcount += 1

            if self.msgcount >= 5:
                time.sleep(self.waittime)
                self.lastmsg = now + self.waittime

class IRCPluginBot(IRCBot):
    def __init__(self, plugin, channels):
        IRCBot.__init__(self, [(plugin.server, plugin.port)], plugin.nick, plugin.nick)
        self.initial_channels = channels
        self.plugin = plugin
        self.ratelimit = RateLimit()
    
    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")
    
    def on_welcome(self, c, e):
        self.plugin.log_message("connected to", self.plugin.server)
        if self.plugin.nickserv_password:
            self.plugin.log_verbose("sending password to NickServ...")
            self.connection.privmsg("NickServ", "identify " + self.plugin.nickserv_password)
        for chan in self.initial_channels:
            c.join(chan)
        self.plugin.connected = True
    
    def strip_nonprintable(self, s):
        return ''.join([c for c in s if c in string.printable])
    
    def on_privmsg(self, c, e):
        msg = e.arguments[0].strip()
        msg = self.strip_nonprintable(msg)
        self.do_command(e.source.nick, None, msg)
        
    def on_pubmsg(self, c, e):
        channel = e.target
        msg = e.arguments[0].strip()
        msg = self.strip_nonprintable(msg)
        def reply(msg):
            self.ratelimit.call()
            self.connection.privmsg(channel, msg)
        self.plugin.do_input([channel], e.source.nick, msg, False, reply)
    
    def do_command(self, source, channel, cmd):
        if cmd == "":
            return
        
        def reply(msg):
            self.ratelimit.call()
            if channel == None:
                self.connection.privmsg(source, msg)
            else:
                self.connection.privmsg(channel, ("%s: %s" % (source, msg)))
        
        channels = []
        if channel != None:
            channels.append(channel)
        else:
            for chan in self.channels:
                if self.channels[chan].has_user(source):
                    channels.append(chan)
        self.plugin.do_input(channels, source, cmd, True, reply)

class IRCPlugin(Plugin):
    """The IRC plugin. This listens for messages on the configured IRC channels
    and relays them to the core on the configured hesperus plugin channels.

    You can also specify separate hesperus channels for particular users. When
    a user either sends a private message to us or says something in a channel,
    this plugin will add the configured hesperus channel to the resulting call
    to parent.handle_incoming()

    Using this technique, you can form a rudimentary access list for certain
    plugins. Say you configure this plugin to join an irc channel and have it
    associate with hesperus channel "default". Then you add a nick with the
    plugin "admin". Then you can plugins that listen to "default" and respond
    to everyone, and plugins that respond to "admin" and will get messages only
    from admins.

    """

    @Plugin.config_types(server=str, port=int, nick=str, nickserv_password=str, channelmap=ET.Element, nickmap=ET.Element, quitmsgs=ET.Element)
    def __init__(self, core, server='chat.freenode.net', port=6667, nick='hesperus', nickserv_password=None, channelmap=None, nickmap=None, quitmsgs=None):
        
        super(IRCPlugin, self).__init__(core)
        
        self.server = server
        self.port = port
        self.nick = nick
        self.nickserv_password = nickserv_password
        self.chanmap = {}
        self.nickmap = {}
        
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

        if quitmsgs is None or len(quitmsgs) is 0:
            self.quitmsg = 'Daisy, daisy...'
        else:
            self.quitmsg = [el for el in quitmsgs if el.tag.lower() == 'quitmsg'][int(time.time()) % len(quitmsgs)].text
        
        channels = []
        for k in self.chanmap:
            self.subscribe(k)
            for chan in self.chanmap[k]:
                if not chan in channels:
                    channels.append(chan)
        for k in self.nickmap:
            self.subscribe(k)
        
        self.bot = IRCPluginBot(self, channels)

    @property
    def connected(self):
        with self.lock:
            return getattr(self, "_connected", False)
    @connected.setter
    def connected(self, value):
        with self.lock:
            self._connected = value
        
    def run(self):
        self.log_verbose("connecting...")
        # start() calls _connect() and then reactor.process_forever()... since
        # we want to be in control of the main loop, just call _connect() for
        # now.
        #self.bot.start()
        self.bot._connect()
        try:
            while True:
                self.bot.reactor.process_once()
                yield
        finally:
            # Apparently, IRC servers only use your quit message if you've been
            # connected for more than 5 minutes (according to a comment in
            # irclib). No idea why.
            self.bot.disconnect(self.quitmsg)
    
    @Plugin.queued
    def do_input(self, irc_channels, irc_nick, msg, direct, reply):
        chans = []
        for irc_channel in irc_channels:
            for k in self.chanmap:
                if irc_channel in self.chanmap[k] and not k in chans:
                    chans.append(k)
        for k in self.nickmap:
            if irc_nick in self.nickmap[k] and not k in chans:
                chans.append(k)
        
        self.parent.handle_incoming(chans, irc_nick, msg, direct, reply)
    
    @Plugin.queued
    def send_outgoing(self, chan, msg):
        if chan in self.chanmap:
            for irc_chan in self.chanmap[chan]:
                self.bot.ratelimit.call()
                self.bot.connection.privmsg(irc_chan, msg)
        if chan in self.nickmap:
            for irc_nick in self.nickmap[chan]:
                self.bot.ratelimit.call()
                self.bot.connection.privmsg(irc_nick, msg)
