from hesperus.core import Core
import sys

try:
    c = Core.load_from_file(sys.argv[1])
except IndexError:
    print "Give me a config file to run!"

try:
    c.start()
except KeyboardInterrupt:
    c.stop()
    print "caught ^C, exiting..."

