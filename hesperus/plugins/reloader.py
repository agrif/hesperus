import time

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
        self.skip.add(self.__class__.__name__)
        if skip == None:
            skip = []
        for el in skip:
            if not el.tag.lower() == 'name':
                raise ConfigurationError('skip must contain name tags')
            self.skip.add(el.text.strip())

    @CommandPlugin.register_command("reload")
    def reload(self, chans, name, match, direct, reply):
        self.log_message("Reloading plugins...")
        reply("Reloading all plugins.. STAND BY!")

        for plugin in list(self.parent.plugins):
            if plugin is self:
                self.log_debug("Skipping reloader plugin")
                continue

            if plugin.__class__.__name__ in self.skip:
                self.log_debug("Skipping %s as per configuration" % plugin.__class__.__name__)
                continue

            self.log_verbose("Removing plugin %s" % plugin.__class__.__name__)
            self.parent.remove_plugin(plugin, True)

        self.log_verbose("Done unloading plugins... now to reload them")
        # Now that they're all unloaded, reload them:
        config = ET.parse(self.parent.configfile).getroot()
        for el in config:
            if el.tag.lower() == 'plugin':
                # Before we go and call Plugin.load_plugin, we need to get a
                # handle to the plugin's module and then call reload() on it,
                # to force Python to purge the old module from sys.modules and
                # use the new one.
                plug_type = el.get('type')
                modulename, pluginname = plug_type.rsplit(".", 1)

                # Check if this is one of the to-be-skipped plugins
                if pluginname in self.skip:
                    self.log_debug("Not reloading %s from module %s" % (pluginname, modulename))
                    continue

                self.log_verbose("Reloading module %s for plugin %s" % (modulename, pluginname))
                mod = __import__(modulename, fromlist=[pluginname])
                newmod = reload(mod)

                self.log_verbose("Loading plugin %s" % pluginname)
                plugin = Plugin.load_plugin(self.parent, el)
                self.parent.add_plugin(plugin)
                

        reply("Done! Phew, I always get a bit nervous when I do that")
