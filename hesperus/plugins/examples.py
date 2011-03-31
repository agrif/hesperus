from ..plugin import Plugin, CommandPlugin
import time

# a simple command-based plugin, note all commands will
# run in the same thread
class ExampleCommandPlugin(CommandPlugin):
    @CommandPlugin.register_command("test (.*)")
    def test_command(self, chans, match, direct, reply):
        reply("got test command, %s" % (match.group(1),))

# a polling-based plugin, that checks an external source for info
# in its own thread, periodically
# this can be combined with the command plugin, too! The poll thread
# is the same thread as the one where commands run
# hence, yield every so often to allow those commands to run!
class ExamplePollPlugin(Plugin):
    def run(self):
        self.lasttime = time.time()
        while True:
            # poll every 5 seconds
            while time.time() < self.lasttime + 5.0:
                yield
            
            # fetch some page, or something here
            #urllib.open(...)
            yield
            
            # act on the fetch, by sending a message
            # to our subscribed channels
            for chan in self.channels:
                self.parent.send_outgoing(chan, "poll every 5 seconds")
            yield

# a configuration-reading plugin
# will read
#####################################
# <plugin ...>
#     <setting-one>data</setting-one>
#     <other>199</other>
# </plugin>
####################################
# note this can be combined with all of the above!
class ExampleConfigPlugin(Plugin):
    @Plugin.config_types(setting_one=str, other=int)
    def __init__(self, core, setting_one="default", other=0):
        super(ExampleConfigPlugin, self).__init__(core)
        
        # do something with setting_one, other
        pass
