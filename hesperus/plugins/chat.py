from ..plugin import CommandPlugin, Plugin
from ..core import ET, ConfigurationError
from ..agent import Agent

class ChatPlugin(Plugin):
    """This plugin is the controller class for ChatModule objects (see docs on
    ChatModule below).

    The configuration takes one element: "modules". Each module
    tag within loads the given class as a ChatModule.

    Example:
        <plugin type="hesperus.plugins.chat.ChatPlugin" channels="default>
            <modules>
                <module>chatmodules.MyChatModuleClass</module>
            </modules>
        </plugin>

    """

    @Plugin.config_types(modules=ET.Element)
    def __init__(self, core, modules=None):
        super(ChatPlugin, self).__init__(core)

        # Maps ChatModule objects to their current callback
        self.modules = {}

        if modules == None:
            modules = []
        for el in modules:
            if not el.tag.lower() == "module":
                raise ConfigurationError("modules must contain <module> tags")
            modname = el.text

            # Load the python module with the given name and get the ChatModule
            # module out of it
            mod = modname.rsplit(".", 1)
            if len(mod) == 1:
                modcls = __import__(mod[0])
            else:
                modcls = getattr(__import__(mod[0], fromlist=[mod[1]]), mod[1])

            instance = modcls()
            self.modules[instance] = instance.trigger

    def run(self):
        try:
            # Start the plugins
            for mod in self.modules.iterkeys():
                mod.start_threaded()

            while True:
                yield
                # Check all ChatModules to make sure they're still running
                for mod in self.modules.iterkeys():
                    if not mod.running:
                        return
                    yield
        finally:
            for mod in self.modules.iterkeys():
                mod.stop()

    @Agent.queued
    def handle_incoming(self, chans, name, msg, direct, reply):
        super(ChatPlugin, self).handle_incoming(chans, name, msg, direct, reply)

        for mod, callback in self.modules.iteritems():
            ret = callback(name, msg, direct, reply)
            if ret:
                # Set new callback
                self.modules[mod] = ret
            else:
                # Set default callback
                self.modules[mod] = mod.trigger
        

class ChatModule(Agent):
    """An abstract class defining the interface for chat modules. Not to be
    confused with the Python notion of a "module".

    A chat module is class that listens to chat lines and responds depending on
    its logic.

    Modules are instantiated when the controller loads and remain in memory for
    the duration of the controller's life.

    ChatModule objects have a simpler interface than a normal hesperus plugin.
    ChatModules have no notion of channels like hesperus plugins, instead every
    line of input sent to the core plugin is relayed to each ChatModule.

    By default, for each line of input, the ChatPlugin core calls each module's
    trigger() method. The call can be changed with a simple interface to easily
    make state machines. See the docs for the trigger() method for more
    information.

    ChatModules inherit from Agent, so they are free to use @Agent.queued to
    run certain callbacks asynchronously, use the self.log_*() methods, or
    override their run() method to perform asynchronous tasks outside of the
    context of a callback. Remember: the run() method should not return and
    should yield once in a while to let queued methods get processed.

    """

    def trigger(self, name, msg, direct, reply):
        """This method is called for every chat line by default.
        
        If the method returns a callable, the given callable will be called for
        future lines of chat instead of this one. Otherwise, this method
        remains as the method called for new lines.
        
        The callable's signature is the same as trigger(), and its semantics
        are similar: if it returns None then the trigger() method is reset as
        the callback, if it returns a callable, the given callable is used for
        all further lines. Thus, a callable must return itself in order to
        remain the callback for new lines.

        This makes it easy to create simple state machines by manipulating the
        callback function as a state variable. For simpler chat modules or ones
        with logic that doesn't fit this pattern, trigger could always return
        None to ignore that logic.

        the reply parameter is a callback used to reply to the source of the
        message that triggered the current method call.

        direct is a boolean used to distinguish between messages directed
        specifically at us, or general messages. Warning: if direct is True,
        the reply callback probably has "name: " automatically prepended to the
        given reply message.

        name is the username of the user that send the message, or None if
        there isn't one or it doesn't apply.

        msg is the message that triggered this callback.

        """
        raise NotImplementedError("Implement me!")

