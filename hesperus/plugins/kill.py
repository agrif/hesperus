from hesperus.plugin import CommandPlugin

class KillPlugin(CommandPlugin):
    commands_queued = False
    @CommandPlugin.register_command(r"kill|die")
    def kill_command(self, chans, name, match, direct, reply):
        self.log_message("kill command issued by %s!" % (name,))
        reply(":( Shutting down...")
        self.parent.stop()

class KillPluginAsync(CommandPlugin):
    """Runs the commands in the plugin thread"""
    commands_queued = True

    @CommandPlugin.register_command(r"killasync")
    def kill_command(self, chans, name, match, direct, reply):
        self.log_message("kill command issued by %s!" % (name,))
        reply(":( Shutting down...")
        self.parent.stop()
