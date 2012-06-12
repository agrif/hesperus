from agent import Agent
from xml.etree import ElementTree as ET
import time
from copy import copy
import traceback
import re

class ConfigurationError(Exception):
    pass

class Plugin(Agent):
    """A plugin is an Agent with the addition of some configuration routines
    and a message passing interface for inter-plugin communication.

    Each Plugin can send and receive messages on "channels".  A plugin is
    configured with a number of channels that it "listens to" and will receive
    messages on. When the core receives an incoming message, it is relayed to
    all plugins whose channels intersect with the message's channels.

    Plugins can also send messages, for example, if they communicate with an
    external service such as IRC. When the core receives an outgoing message,
    it is sent to all plugins who are subscribed to the message's destination
    channel.

    All plugins have a "parent" which is typically the core. Plugins can send
    incoming and outgoing messages to the core and they will be relayed to the
    other plugins depending on the message and the plugin channels.

    Typically, plugins will fall into one of two categories: a connector to a
    service such as IRC, or a plugin that provides some kind of functionality
    in response to messages from the service connector.

    For example, the IRC plugin connects to an IRC server. New messages are
    sent to the core and to other plugins via parent.handle_incoming(). Plugins
    respond by calling either the reply() callback provided to
    handle_incoming(), or by calling parent.send_outgoing() to relay a message
    to the IRC plugin.

    """

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
                traceback.print_exc()
                raise ConfigurationError('invalid plugin type "%s"' % (plug_type,))
        else:
            try:
                plugcls = __import__(mod[0], fromlist=[mod[1]])
                plugcls = getattr(plugcls, mod[1])
            except (ImportError, AttributeError):
                traceback.print_exc()
                raise ConfigurationError('invalid plugin type "%s"' % (plug_type,))

        try:
            plug = plugcls(core, **kwargs)
        except TypeError, e:
            traceback.print_exc()
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
                    elif types[k] == bool:
                        # special bool handling
                        if not isinstance(kwargs[k], bool) and isinstance(kwargs[k], str):
                            if kwargs[k].lower() in ['true', '1']:
                                kwargs[k] = True
                            elif kwargs[k].lower() in ['false', '0']:
                                kwargs[k] = False
                        if not isinstance(kwargs[k], bool):
                            raise ConfigurationError('tag "%s" is not a bool' % (k,))
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

    def handle_incoming(self, chans, name, msg, direct, reply):
        """Handle incoming messages. chans contains a list of channels
        that the author of this message belongs to. name is the name
        of the author (or None, if the source doesn't support
        names). msg contains the text itself, possibly stripped of
        non-important information. direct is True if the message was
        directed at us, or False if not. reply is a function that
        accepts a string as an argument, and will reply to this
        message."""
        #self.log_debug("incoming", self, chans, msg, direct, reply)
        pass

    def send_outgoing(self, chan, msg):
        """Send non-directed text to the given channel. chan holds the
        destination channel, and msg is the message to send."""
        #self.log_debug("outgoing", self, chan, msg)
        pass

# special case of Plugin that just handles chat commands, given as regexps
class CommandPlugin(Plugin):
    """Plugins deriving from this class are meant to implement a command that
    users issue to the bot and the bot will perform some action and respond.

    It provides a register_command decorator which takes as an argument a
    regular expression string to match.

    This class also implements handle_incoming() which will dispatch as
    appropriate to functions with the register_command decorator applied whose
    regular expression matches the incoming message.

    The decorated functions are passed as the message the command portion of
    the message. In other words, the part of the message that matched the given
    regular expression.

    """
    # If true, incomming messages will be added to the agent's built-in queue
    # and handled in the plugin's thread instead of the core thread
    commands_queued = True

    # first, the decorator for defining commands
    # takes a regexp to match, and direct-only flag (default=True)
    # applies to a function taking (chans, match_obj, direct, reply)
    @classmethod
    def register_command(cls, regexp, direct_only=True):
        regexp = re.compile(regexp + "$")
        def sub_generator(func):
            def sub_function(self, chans, name, msg, direct, reply):
                if direct_only and not direct:
                    return False
                match = regexp.match(msg)
                if not match:
                    return False
                func(self, chans, name, match, direct, reply)
                return True

            sub_function._hesperus_command = True
            return sub_function
        return sub_generator

    def handle_incoming(self, *args):
        if self.commands_queued:
            self.handle_incoming_queued(*args)
        else:
            self.handle_incoming_nonqueued(*args)

    def handle_incoming_nonqueued(self, chans, name, msg, direct, reply):
        for func in dir(self):
            func = getattr(self, func)
            if (not "_hesperus_command" in dir(func)) or (not func._hesperus_command):
                continue
            if func(chans, name, msg, direct, reply):
                return
    handle_incoming_queued = Plugin.queued(handle_incoming_nonqueued)

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

# special case of command plugin that looks for patterns in messages and
#  does something with them
class PassivePlugin(CommandPlugin):
    @classmethod
    def register_pattern(cls, regexp, ignore_direct=False):
        """The decorated method will be called for every line of chat that matches the given regexp.
        You can return True to indicate no other command handlers will be
        called; the line was "hanlded". Otherwise, other commands that may also
        match will also be called.

        if ignore_direct is true, ignores messages that are directed
        specifically at us

        """
        pattern = re.compile(regexp)
        def wrapper(func):
            def wrapped(self, chans, name, msg, direct, reply):
                if direct and ignore_direct:
                    return False
                match = pattern.search(msg)
                if match:
                    try:
                        return func(self, match, reply)
                    except TypeError:
                        return func(self, chans, name, match, direct, reply)
                else:
                    return False
            wrapped._hesperus_command = True
            return wrapped
        return wrapper

class PersistentPlugin(Plugin):
    persitence_file = 'global.json'
    _data = {}

    def save_data(self):
        with open(self.persitence_file, 'w') as pf:
            json.dump(self._data, pf)

    def load_data(self):
        try:
            with open(self.persitence_file, 'r') as pf:
                self._data.update(json.load(pf))
        except IOError as e:
            self.log_warning('Error while loading persistent data: {}'.format(e))
