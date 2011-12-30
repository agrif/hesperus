from hesperus.core import Core
import sys

c = Core.load_from_file(sys.argv[1])
try:
    c.start()
except KeyboardInterrupt:
    c.stop()
    print "caught ^C, exiting..."

