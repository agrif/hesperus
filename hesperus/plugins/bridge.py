from ..core import ConfigurationError, ET
from ..plugin import Plugin

class BridgePlugin(Plugin):
    @Plugin.config_types(inputs=ET.Element, outputs=ET.Element)
    def __init__(self, core, inputs=None, outputs=None):
        super(BridgePlugin, self).__init__(core)
        
        self.inputs = []
        if inputs == None:
            inputs = []
        for el in inputs:
            if not el.tag.lower() == 'input':
                raise ConfigurationError('inputs must contain input tags')
            channel = el.text.strip()
            self.subscribe(channel)
            self.inputs.append(channel)
        
        self.outputs = []
        if outputs == None:
            outputs = []
        for el in outputs:
            if not el.tag.lower() == 'output':
                raise ConfigurationError('outputs must contain output tags')
            channel = el.text.strip()
            self.subscribe(channel)
            self.outputs.append(channel)
    
    def handle_incoming(self, chans, name, msg, direct, reply):
        other_chans = set(chans) - set(self.inputs)
        chans = set(chans).intersection(self.inputs)
        if not chans:
            return
        
        # direct *usually* means private message, so don't broadcast those!
        if not direct:
            for chan in self.inputs:
                if chan in chans:
                    continue
                self.parent.send_outgoing(chan, '<%s> %s' % (name, msg))
            
            old_reply = reply
            def new_reply(msg):
                for chan in self.inputs:
                    self.parent.send_outgoing(chan, msg)
            reply = new_reply
        
        self.parent.handle_incoming(self.outputs + list(other_chans), name, msg, direct, reply)
    
    def send_outgoing(self, chan, msg):
        if not chan in self.outputs:
            return
        
        for inchan in self.inputs:
            self.parent.send_outgoing(inchan, msg)
