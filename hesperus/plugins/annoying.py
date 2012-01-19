import random
import time
import re

from ..plugin import Plugin

class Repeater(Plugin):
    """If the bot sees the same chat line two or more times, has a random
    chance to join in and repeat it.

    TODO: Keep track of what channels the lines came from so there's not a
    small chance it'll repeat a line it saw in two different channels
    """
    matcher = re.compile(r"^[^! ][^ ]{0,5}$")
    timeout = 5

    def __init__(self, *args):
        super(Repeater, self).__init__(*args)
        self.lastline = None
        self.lastmsg = 0
        
    @Plugin.queued
    def handle_incoming(self, chans, name, msg, direct, reply):
        if direct: return

        match = self.matcher.match(msg)
        if match:
            pass
            #self.log_debug("Line %s matched" % msg)
        else:
            # Clear last line
            self.lastline = None
            return

        if time.time() < self.lastmsg + self.timeout:
            return

        if msg == self.lastline:
            rnd = random.random()
            self.log_debug("A repeat! Random chance was %s" % rnd)
            if rnd < 0.7:
                self.log_debug("Repeating the line! Incomming!")
                time.sleep(2)
                reply(msg)
        else:
            self.lastline = msg

class NoU(Plugin):
    """Watches for someone to say NO U and then tosses it back at them

    """
    noumatch = re.compile(r"^no+ ?u!*$", re.I)
    nomatch = re.compile(r"^no+!*$", re.I)
    umatch = re.compile(r"^u+!*", re.I)
    timeout = 2

    def __init__(self, *args):
        super(NoU, self).__init__(*args)
        self.lastmsg = 0
        self.noseen = False

    #def trigger(self, name, msg, direct, reply):
    @Plugin.queued
    def handle_incoming(self, chans, name, msg, direct, reply):
        if time.time() < self.lastmsg + self.timeout:
            return

        if self.noumatch.match(msg):

            self.lastmsg = time.time()
            time.sleep(2)
            reply(msg + "!")
            return

        elif self.noseen:
            self.u(msg, reply)

        elif self.nomatch.match(msg):
            self.log_debug("'no' detected. looking for a 'u'")
            self.noseen = True

    def u(self, msg, reply):
        if self.umatch.match(msg):
            self.log_debug("u found. here it comes!")
            self.lastmsg = time.time()
            time.sleep(2)
            reply("NO U!")
        else:
            self.log_debug("Guess not.")
        self.noseen = False
