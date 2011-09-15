from hesperus.plugin import CommandPlugin
from datetime import datetime

class SeenPlugin(CommandPlugin):
    def __init__(self, core):
        super(SeenPlugin, self).__init__(core)
        self.times = {}
        self.starttime = datetime.utcnow()
    
    @CommandPlugin.register_command(r"(seen|lastseen)(?:\s+(.*?))?(?:\?)?")
    def seen_command(self, chans, name, match, direct, reply):
        cmd = match.group(1)
        target = match.group(2)
        
        if not target:
            reply("usage: %s <username>" % (cmd,))
            return
        
        def fmtdate(d):
            now = datetime.utcnow()
            delta = now - d
            delta = delta.seconds + delta.days * 24 * 60 * 60
            if delta > 60 * 60 * 24 * 7:
                return d.strftime("on %B %d, %Y")
            elif delta > 60 * 60 * 24:
                delta /= 60 * 60 * 24
                return "%i day%s ago, on %s" % (delta, '' if delta == 1 else 's', d.strftime("%A, %B %d"))
            elif delta > 60 * 60:
                delta /= 60 * 60
                return "%i hour%s ago" % (delta, '' if delta == 1 else 's')
            elif delta > 60:
                delta /= 60
                return "%i minute%s ago" % (delta, '' if delta == 1 else 's')
            
            return "%i seconds ago" % (delta,)
        
        if not target in self.times:
            reply("%s has not been seen since I started watching %s." % (target, fmtdate(self.starttime)))
        else:
            reply("%s was last seen %s." % (target, fmtdate(self.times[target])))
    
    @CommandPlugin.queued
    def update_seen(self, name):
        self.times[name] = datetime.utcnow()
    
    def handle_incoming(self, chans, name, msg, direct, reply):
        super(SeenPlugin, self).handle_incoming(chans, name, msg, direct, reply)
        self.update_seen(name)
