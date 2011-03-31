from copy import copy

class Plugin(Agent):
    def __init__(self, parent, channels=[], daemon=False):
        super(Plugin, self).__init__(daemon=daemon)
        self._channels = copy(channels)
        self.parent = parent
    
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
        self.log_debug("incoming", self, chans, msg, direct, reply)
    
    def send_outgoing(self, chan, msg):
        """Send non-directed text to the given channel. chan holds the
        destination channel, and msg is the message to send."""
        self.log_debug("outgoing", self, chan, msg)
