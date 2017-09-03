import time
import traceback
import random

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

    @CommandPlugin.register_command(r"unload (\w+)")
    def unload(self, chans, name, match, direct, reply):
        for plugin in self.parent.plugins:
            if plugin.__class__.__name__ == match.group(1):
                self.parent.remove_plugin(plugin)
                reply("%s unloaded" % match.group(1))
                break
        else:
            reply("No running plugin named %s found" % match.group(1))

    @CommandPlugin.register_command(r"(?:load|reload)(?: (\w+))?")
    def reload(self, chans, name, match, direct, reply):
        self.log_message("Reloading plugins...")

        # Do an early check to see if the config is malformed
        try:
            config = ET.parse(self.parent.configfile).getroot()
        except Exception:
            traceback.print_exc()
            reply("Error reading config file. No plugins (re)loaded")
            return

        # Get the set of current plugin names
        loadedplugins = set(x.__class__.__name__ for x in list(self.parent.plugins))

        if match.group(1):
            # A specific plugin was requested for reload
            toreload = set([match.group(1)])

        else:
            # Reload all but the ones in the skip list
            toreload = loadedplugins.difference(self.skip)
            if not toreload:
                reply("No plugins to reload. Specify a specific plugin to reload with 'reload <pluginname>'")
                return

        self.log_debug("Reloading these plugins: %r" % (toreload,))
        affirms = ["Yes sir!", "Right away sir!", "Sure thing, boss!", "You got it!"]
        if not match.group(1) or match.group(1) in loadedplugins:
            # Only do this reply if we're either reloading everything or if
            # we're loading a specific plugin that is already loaded.
            # Skip the case of reloading a plugin that is not loaded, we don't
            # know yet whether it exists to load or doesn't exist at all.
            reply(random.choice(affirms))

        #############
        # Unload procedure
        oldircplugin = None
        foundunload = False
        for plugin in list(self.parent.plugins):

            pluginname = plugin.__class__.__name__

            if pluginname == "IRCPlugin":
                oldircplugin = plugin

            if pluginname not in toreload:
                continue

            foundunload = True

            self.log_verbose("Removing plugin %s" % plugin.__class__.__name__)
            # Remove the plugin. Only wait for it to unload if we're not unloading ourself
            self.parent.remove_plugin(plugin, pluginname != self.__class__.__name__)

        self.log_verbose("Done unloading plugins... now to reload them")

        #############
        # (Re-)load procedure
        errorlist = []
        ircplugin = None
        foundreload = False
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

                foundreload = True

                self.log_verbose("Reloading module %s for plugin %s" % (modulename, pluginname))
                try:
                    mod = __import__(modulename, fromlist=[pluginname])
                    newmod = reload(mod)
                except Exception, e:
                    traceback.print_exc()
                    errorlist.append(pluginname)
                else:

                    self.log_verbose("Loading plugin %s" % pluginname)
                    try:
                        plugin = Plugin.load_plugin(self.parent, el)
                    except ConfigurationError, e:
                        self.log_message("Configuration error in %s: %s" % (pluginname,e,))
                        errorlist.append(pluginname)
                    except Exception, e:
                        self.log_message("Misc error in %s: %s" % (pluginname, e))
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

        if match.group(1) and not foundunload and not foundreload:
            # A specific plugin was requested but it was neither unloaded or
            # reloaded.
            reply("There is no such plugin to reload!")
        elif not errorlist:
            if match.group(1) and not foundunload:
                reply("Loaded %s!" % match.group(1))
            elif match.group(1) and not foundreload:
                reply("Unloaded %s!" % match.group(1))
            else:
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

