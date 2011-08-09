from hesperus.plugin import CommandPlugin

class WhoAmIPlugin(CommandPlugin):
    @CommandPlugin.register_command(r"whoami|[Ww]ho\s+am\s+[Ii]\??")
    def kill_command(self, chans, name, match, direct, reply):
        reply("You are '%s', in channels %s" % (name, repr(chans)))
