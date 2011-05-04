from hesperus.plugin import CommandPlugin

class KillPlugin(CommandPlugin):
    @CommandPlugin.register_command(r"kill")
    def kill_command(self, chans, match, direct, reply):
        self.log_message("kill command issued!")
        reply(":( Shutting down...")
        self.parent.stop()
