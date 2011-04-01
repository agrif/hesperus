from hesperus.core import Core
from hesperus.plugin import Plugin
from hesperus.plugins.irc import IRCPlugin
import time, random, sys

###########################

c = Core.load_from_file(sys.argv[1])
c.start()
