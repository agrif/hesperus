import time
import traceback

from ..plugin import CommandPlugin, Plugin
from ..core import ConfigurationError, ET

class Reloader(CommandPlugin):

    def __init__(self, core, skip=None):
        """Initialize the reloader plugin.

        skip is an element tree of plugin class names to skip unless explicitly
        specified

        """
        super(Reloader, self).__init__(core)

        self.skip = set()
        if skip == None:
            skip = []
        for el in skip:
            if not el.tag.lower() == 'name':
                raise ConfigurationError('skip must contain name tags')
            self.skip.add(el.text.strip())

    @CommandPlugin.register_command(r"reload(?: (\w+))?")
    def reload(self, chans, name, match, direct, reply):
        self.log_message("Reloading plugins...")

        # Get the set of current plugins
        toreload = set(x.__class__.__name__ for x in list(self.parent.plugins))

        if match.group(1):
            # A specific plugin was requested for reload
            if not match.group(1) in toreload:
                reply("I'm not running a plugin called %s!" % match.group(1))
                return
            toreload = set([match.group(1)])

        else:
            # Reload all but the ones in the skip list
            toreload.difference_update(self.skip)
            if not toreload:
                reply("No plugins to reload. Specify a specific plugin to reload with 'reload <pluginname>'")
                return

        self.log_debug("Reloading these plugins: %r" % (toreload,))
        reply("Yes sir!")

        oldircplugin = None
        for plugin in list(self.parent.plugins):

            pluginname = plugin.__class__.__name__

            if pluginname == "IRCPlugin":
                oldircplugin = plugin

            if pluginname not in toreload:
                continue

            self.log_verbose("Removing plugin %s" % plugin.__class__.__name__)
            # Remove the plugin. Only wait for it to unload if we're not unloading ourself
            self.parent.remove_plugin(plugin, pluginname != self.__class__.__name__)

        self.log_verbose("Done unloading plugins... now to reload them")

        # Now that they're all unloaded, reload them:
        config = ET.parse(self.parent.configfile).getroot()
        errorlist = []
        ircplugin = None
        for el in config:
            if el.tag.lower() == 'plugin':
                # Before we go and call Plugin.load_plugin, we need to get a
                # handle to the plugin's module and then call reload() on it,
                # to force Python to purge the old module from sys.modules and
                # use the new one.
                plug_type = el.get('type')
                modulename, pluginname = plug_type.rsplit(".", 1)

                # Check if this is one of the plugins we're supposed to load
                if pluginname not in toreload:
                    continue

                self.log_verbose("Reloading module %s for plugin %s" % (modulename, pluginname))
                mod = __import__(modulename, fromlist=[pluginname])
                try:
                    newmod = reload(mod)
                except Exception, e:
                    traceback.print_exc()
                    errorlist.append(pluginname)
                else:

                    self.log_verbose("Loading plugin %s" % pluginname)
                    try:
                        plugin = Plugin.load_plugin(self.parent, el)
                    except ConfigurationError, e:
                        errorlist.append(pluginname)
                    else:
                        self.parent.add_plugin(plugin)
                
                # Special provisions for reloading the IRC plugin, since the
                # reply() method will no longer be valid
                if pluginname == "IRCPlugin":
                    ircplugin = plugin
                

        if ircplugin and oldircplugin:
            # We have reloaded the ircplugin. We cannot use the given reply()
            # method because that connection to the server has been severed.
            # XXX Terrible hack incomming!!! Warning!
            # The old IRCPlugin object is still hanging around in memory.  We
            # cannot edit the reply() method or even know what it does, but we
            # CAN replace the connection object in the old IRCPlugin object
            # with the new one.
            # If we survive the rest of this method, we should be okay since
            # the old IRCPlugin object should be garbage collected very soon.
            self.log_debug("Waiting for IRC to re-connect")
            while not ircplugin.connected:
                time.sleep(0.5)
            oldircplugin.bot.connection = ircplugin.bot.connection
            self.log_debug("IRC connected. Swapping connection object and proceeding to reply...")
            time.sleep(1)

        if not errorlist:
            reply("Reload complete, boss!")
        else:
            if len(errorlist) == 1:
                reply("Sorry boss, I couldn't reload %s" % errorlist[0])
            elif len(errorlist) == 2:
                reply("Sorry boss, I couldn't reload %s" % " and ".join(errorlist))
            else:
                s = ", ".join(errorlist[:-1])
                s += ", and " + errorlist[-1]
                reply("Sorry boss, I couldn't reload %s" % s)

            
        self.log_message("Reloading complete")

    @CommandPlugin.register_command("listplugins")
    def list_command(self, chans, name, match, direct, reply):
        reply("I'm currently running the following plugins: %s" %
                ", ".join(p.__class__.__name__ for p in self.parent.plugins)
                )

