from agent import Agent
from xml.etree import ElementTree as ET
import time

class ConfigurationError(Exception):
    pass

from plugin import Plugin

class Core(Agent):
    @classmethod
    def load_from_file(cls, fname):
        config = ET.parse(fname).getroot()
        c = Core()
        
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
        
        super(Core, self).start()
        
        with self.lock:
            for plug in self._plugins:
                if plug.running:
                    plug.stop()
    
    def run(self):
        while True:
            for plug in self.plugins:
                if plug.error:
                    # print out error, and quit
                    self.log_error("error in", plug)
                    with self.__class__.stdout_lock:
                        print plug.error[1],
                    return
                
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
    def handle_incoming(self, chans, msg, direct, reply):
        for plug in self.plugins:
            relevant_chans = set(plug.channels).intersection(set(chans))
            if len(relevant_chans) > 0:
                plug.handle_incoming(list(relevant_chans), msg, direct, reply)
    
    @Agent.queued
    def send_outgoing(self, chan, msg):
        for plug in self.plugins:
            if chan is plug.channels:
                plug.send_outgoing(self, chan, msg)
