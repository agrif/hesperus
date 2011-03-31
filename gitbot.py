from hesperus.core import Core
from hesperus.plugin import Plugin
from hesperus.plugins.irc import IRCPlugin
import time, random

###########################

c = Core()

p = Plugin(c)
p.subscribe('default')
c.add_plugin(p)

irc = IRCPlugin(c, 'irc.freenode.net', 6667, 'hesperus-bot', {'default' : ['#moosesocks']})
c.add_plugin(irc)

c.start()
