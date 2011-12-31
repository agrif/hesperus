from hesperus.plugin import CommandPlugin

class ListPlugin(CommandPlugin):

    @CommandPlugin.register_command("listplugins")
    def list_command(self, chans, name, match, direct, reply):
        reply("I'm currently running the following plugins: %s" %
                ", ".join(p.__class__.__name__ for p in self.parent.plugins)
                )

