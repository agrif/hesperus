from hesperus.core import Core
from hesperus.plugin import Plugin
from hesperus.plugins.irc import IRCPlugin
import time, random

###########################

c = Core.load_from_file('config.xml')
c.start()
