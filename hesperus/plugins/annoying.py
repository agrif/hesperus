import random
import time
import re

from ..plugin import Plugin, PassivePlugin
from ..core  import ET

class Repeater(Plugin):
    """If the bot sees the same chat line two or more times, has a random
    chance to join in and repeat it.

    TODO: Keep track of what channels the lines came from so there's not a
    small chance it'll repeat a line it saw in two different channels
    """
    matcher = re.compile(r"^[^! ][^ ]{0,5}$")

    @Plugin.config_types(timeout=int, chance=float, exceptions=ET.Element)
    def __init__(self, core, timeout=5, chance=0.7, exceptions=None, *args):
        super(Repeater, self).__init__(core, *args)
        self.lastline = None
        self.lastmsg = 0
        self.timeout = timeout
        self.chance = chance
        self.ignore_names = [el.text.strip().lower() for el in (exceptions if exceptions is not None else []) if el.tag.lower() == 'name']
        
    @Plugin.queued
    def handle_incoming(self, chans, name, msg, direct, reply):
        if direct or name in self.ignore_names: return

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
            if rnd < self.chance:
                self.log_debug("Repeating the line! Incomming!")
                time.sleep(2)
                self.lastmsg = time.time()
                reply(msg)
        else:
            self.lastline = msg

class NoU(Plugin):
    """Watches for someone to say NO U and then tosses it back at them

    """
    noumatch = re.compile(r"^no+ ?u!*$", re.I)
    nomatch = re.compile(r"^no+!*$", re.I)
    umatch = re.compile(r"^u+!*$", re.I)

    @Plugin.config_types(timeout=int, wait=int, chance=float, exceptions=ET.Element)
    def __init__(self, core, timeout=2, wait=2, chance=1.0, exceptions=None, *args):
        super(NoU, self).__init__(core, *args)
        self.lastmsg = 0
        self.noseen = False
        self.timeout = timeout
        self.wait = wait
        self.chance = chance
        self.ignore_names = [el.text.strip().lower() for el in (exceptions if exceptions is not None else []) if el.tag.lower() == 'name']

    @Plugin.queued
    def handle_incoming(self, chans, name, msg, direct, reply):
        if name in self.ignore_names: return
        if time.time() < self.lastmsg + self.timeout:
            return

        if self.noumatch.match(msg):
            if random.random() > self.chance:
                self.log_message("Matched nou but failed random test. %r" % msg)
                return
            self.lastmsg = time.time()
            time.sleep(self.wait)
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
            time.sleep(self.wait)
            self.lastmsg = time.time()
            reply("NO U!")
        else:
            self.log_debug("Guess not.")
        self.noseen = False

class ORLY(Plugin):
    orlymatch = re.compile(r"^o\ ?rly\?*$", re.I)

    @Plugin.config_types(timeout=int, chance=float)
    def __init__(self, core, timeout=5, chance=1.0, *args):
        super(ORLY, self).__init__(core, *args)
        self.lastmsg = 0
        self.timeout = timeout
        self.chance = chance

    @Plugin.queued
    def handle_incoming(self, chans, name, msg, direct, reply):
        if time.time() < self.lastmsg + self.timeout:
            return

        if self.orlymatch.match(msg):
            if random.random() > self.chance:
                self.log_message("Matched orly but failed random test. %r" % msg)
                return

            time.sleep(2)
            self.lastmsg = time.time()
            reply("YA RLY!")
            return

class ThatsWhatSheSaid(PassivePlugin):
    PHRASE = 'That\'s what {pronoun} said!'
    
    @PassivePlugin.config_types(chance=float, max_message_length=int)
    def __init__(self, core, chance=0.1, max_message_length=140, *args):
        super(ThatsWhatSheSaid, self).__init__(core, *args)
        self._chance = chance
        self._max_message_length = max_message_length
    
    @PassivePlugin.register_pattern(r'\b(he|his|she|her|[Ii](?!\')|my(?:self)?|your?)\b')
    def misogyny(self, match, reply):
        if len(match.string) < self._max_message_length:
            pn = match.group(1)
            self.log_debug('Hit on pronoun: %s' % pn)
            roll = random.random()
            if roll < self._chance:
                self.log_debug('Replying, %s < %s' % (roll, self._chance))
                reply(self.PHRASE.format(pronoun=random.choice(['he', 'she'])))
