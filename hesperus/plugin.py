from agent import Agent
from core import ConfigurationError, ET
import time
from copy import copy
import re

class Plugin(Agent):
    @classmethod
    def load_plugin(cls, core, el):
        plug_type = el.get('type', 'plugin.Plugin')
        
        plug_channels = el.get('channels', '').split(',')
        plug_channels = filter(lambda s: len(s) > 0, plug_channels)
        plug_channels = map(lambda s: s.strip(), plug_channels)
        
        kwargs = {}
        for subel in el:
            nice_tag = subel.tag.lower().replace('-', '_')
            if len(subel) == 0:
                kwargs[nice_tag] = subel.text
            else:
                kwargs[nice_tag] = subel
        
        plugcls = None
        mod = plug_type.rsplit('.', 1)
        if len(mod) == 1:
            try:
                plugcls = __import__(mod[0])
            except ImportError:
                raise ConfigurationError('invalid plugin type "%s"' % (plug_type,))
        else:
            try:
                plugcls = __import__(mod[0], fromlist=[mod[1]])
                plugcls = getattr(plugcls, mod[1])
            except (ImportError, AttributeError):
                raise ConfigurationError('invalid plugin type "%s"' % (plug_type,))
        
        try:
            plug = plugcls(core, **kwargs)
        except TypeError, e:
            raise ConfigurationError(str(e))
        
        for chan in plug_channels:
            plug.subscribe(chan)
        
        return plug
        
    def __init__(self, parent, channels=[], daemon=False):
        super(Plugin, self).__init__(daemon=daemon)
        self._channels = copy(channels)
        self.parent = parent
    
    # useful decorator for config type checking
    @classmethod
    def config_types(cls, **types):
        def sub_generator(func):
            def sub_func(self, *args, **kwargs):
                for k in types:
                    if not k in kwargs:
                        continue
                    if types[k] == str:
                        # special string handling
                        if not isinstance(kwargs[k], str):
                            raise ConfigurationError('tag "%s" is not a string' % (k,))
                    elif types[k] == ET.Element:
                        # special element handling
                        try:
                            if not "Element" in kwargs[k].__class__.__name__:
                                raise ConfigurationError('tag "%s" is invalid type' % (k,))
                        except AttributeError:
                            raise ConfigurationError('tag "%s" is invalid type' % (k,))
                    else:
                        try:
                            if not isinstance(kwargs[k], types[k]):
                                kwargs[k] = types[k](kwargs[k])
                        except:
                            raise ConfigurationError('tag "%s" is invalid type' % (k,))
                return func(self, *args, **kwargs)
            return sub_func
        return sub_generator
    
    #
    # channel management
    #
    
    @property
    def channels(self):
        with self.lock:
            return self._channels
    
    def subscribe(self, chan):
        with self.lock:
            if not chan in self._channels:
                self._channels.append(chan)
    
    def unsubscribe(self, chan):
        with self.lock:
            if chan in self._channels:
                self._channels.remove(chan)
    
    def unsubscribe_all(self):
        with self.lock:
            self._channels = []
    
    # override in subclasses, use Plugin.queued when appropriate
    
    def handle_incoming(self, chans, msg, direct, reply):
        """Handle incoming messages. chans contains a list of channels
        that the author of this message belongs to. msg contains the
        text itself, possibly stripped of non-important
        information. direct is True if the message was directed at us,
        or False if not. reply is a function that accepts a string as
        an argument, and will reply to this message."""
        #self.log_debug("incoming", self, chans, msg, direct, reply)
        pass
    
    def send_outgoing(self, chan, msg):
        """Send non-directed text to the given channel. chan holds the
        destination channel, and msg is the message to send."""
        #self.log_debug("outgoing", self, chan, msg)
        pass

# special case of Plugin that just handles chat commands, given as regexps
class CommandPlugin(Plugin):
    # list of registered command functions
    registered_commands = []
    # first, the decorator for defining commands
    # takes a regexp to match, and direct-only flag (default=True)
    # applies to a function taking (chans, match_obj, direct, reply)
    @classmethod
    def register_command(cls, regexp, direct_only=True):
        regexp = re.compile(regexp)
        def sub_generator(func):
            def sub_function(self, chans, msg, direct, reply):
                if direct_only and not direct:
                    return False
                match = regexp.match(msg)
                if not match:
                    return False
                func(self, chans, match, direct, reply)
                return True
            cls.registered_commands.append(sub_function)
            return sub_function
        return sub_generator
    
    @Plugin.queued
    def handle_incoming(self, chans, msg, direct, reply):
        for func in self.registered_commands:
            if func(self, chans, msg, direct, reply):
                return

# special case of plugin that polls every X seconds
class PollPlugin(Plugin):
    poll_interval = 5.0
    
    def run(self):
        self.lasttime = time.time()
        while True:
            while time.time() < self.lasttime + self.poll_interval:
                yield
            
            for _ in self.poll():
                yield
            
            self.lasttime = time.time()
    
    def poll(self):
        yield
