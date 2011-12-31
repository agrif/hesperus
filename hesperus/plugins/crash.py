
from hesperus.plugin import CommandPlugin

"""
These plugins can be used to test the crash handling routines
"""

class CrashPlugin(CommandPlugin):
    commands_queued = False

    @CommandPlugin.register_command("crash")
    def crash_command(self, chans, name, match, direct, reply):
        raise Exception()

class CrashPluginAsync(CommandPlugin):
    """Runs the commands in the plugin thread"""
    commands_queued = True

    @CommandPlugin.register_command("crashasync")
    def crash_command(self, chans, name, match, direct, reply):
        raise Exception()
