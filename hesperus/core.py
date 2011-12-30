import time
import traceback

from agent import Agent
from plugin import Plugin, ConfigurationError, ET

class Core(Agent):
    @classmethod
    def load_from_file(cls, fname):
        config = ET.parse(fname).getroot()
        c = Core()
        c.configfile = fname
        
        for el in config:
            if el.tag.lower() == 'plugin':
                p = Plugin.load_plugin(c, el)
                c.add_plugin(p)
            else:
                raise ConfigurationError('unrecognized tag "%s"' % (tag,))
        
        return c
        
    def __init__(self):
        super(Core, self).__init__()
        self._plugins = []
    
    def start(self):
        with self.lock:
            for plug in self._plugins:
                if not plug.running:
                    plug.start_threaded()
        
        try:
            super(Core, self).start()
        finally:
            with self.lock:
                for plug in self._plugins:
                    if plug.running:
                        plug.stop()
    
    def run(self):
        while True:
            toremove = []
            for plug in self.plugins:
                # There was an error in the plugin's thread that happened asynchronously
                if plug.error:
                    # print out error, and quit
                    self.log_error("error in", plug)
                    self.send_outgoing("default", "One of my plugins, %s, has crashed. Someone call for help plz!"
                            % (plug.__class__.__name__,))
                    with self.__class__.stdout_lock:
                        print plug.error[1],
                    # Can't remove the plugin while we're iterating over the list
                    toremove.append(plug)
                
            for r in toremove:
                self.remove_plugin(r)
            yield
    
    #
    # plugin management
    #
    
    @property
    def plugins(self):
        with self.lock:
            return self._plugins
    
    def add_plugin(self, plug):
        with self.lock:
            if not plug in self._plugins:
                self._plugins.append(plug)
                if self.running and not plug.running:
                    plug.start_threaded()
    
    def remove_plugin(self, plug):
        with self.lock:
            if plug in self._plugins:
                self._plugins.remove(plug)
                if plug.running:
                    plug.stop()
    
    def remove_all_plugins(self):
        with self.lock:
            while len(self._plugins) > 0:
                self.remove_plugin(self._plugins[0])
    
    @Agent.queued
    def handle_incoming(self, chans, name, msg, direct, reply):
        toremove = []
        for plug in self.plugins:
            relevant_chans = set(plug.channels).intersection(set(chans))
            if len(relevant_chans) > 0:
                try:
                    plug.handle_incoming(chans, name, msg, direct, reply)
                except Exception:
                    # An exception occurred in the main thread while calling
                    # into the plugin's handle_incomming method
                    traceback.print_exc()
                    reply("Oh dear, there was a problem in the %s plugin. I'm shutting it down." %
                            (plug.__class__.__name__,))
                    # Can't remove the plugin while we're iterating over the list
                    toremove.append(plug)
        for r in toremove:
            self.remove_plugin(r)
    
    @Agent.queued
    def send_outgoing(self, chan, msg):
        for plug in self.plugins:
            if chan in plug.channels:
                plug.send_outgoing(chan, msg)
