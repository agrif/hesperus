from hesperus.plugin import CommandPlugin

class RemindPlugin(CommandPlugin):
    def __init__(self, core):
        super(RemindPlugin, self).__init__(core)
        self.notices = {}
    
    @CommandPlugin.register_command(r"remind(?:\s+(.*?))?(?:\s+(.*))?")
    def remind_command(self, chans, name, match, direct, reply):
        target = match.group(1)
        message = match.group(2)
        
        if not target or not message:
            reply("usage: remind <username> <message>")
            return
        
        if not target in self.notices:
            self.notices[target] = []
        self.notices[target].append("%s reminds you `%s'" % (name, message))
        
        reply("Reminder saved.")
    
    @CommandPlugin.queued
    def remind_check(self, name, reply):
        if name in self.notices:
            for notice in self.notices[name]:
                reply("%s, %s" % (name, notice))
            del self.notices[name]
    
    def handle_incoming(self, chans, name, msg, direct, reply):
        super(RemindPlugin, self).handle_incoming(chans, name, msg, direct, reply)
        if direct:
            return
        
        self.remind_check(name, reply)
