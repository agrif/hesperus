# encoding: UTF-8
from __future__ import division
import re

from ..plugin import Plugin

class UnitConverter(Plugin):
    c_re = re.compile(r"""
            # Make sure it's either at the beginning of a word, beginning of the
            # line, or at least not proceeded by an alphanumeric character
            (?: \A | \b | [ ] )
            (
                -? # optional minus
                \d+ # Capture a number
            )
            [ ]? # Optional space
            (?: degrees[ ] )? # An optional "degrees " spelled out
            (?: ° )? # An optional degrees sign would go here if we got unicode
            C # Capital C
            \b # only capture at word boundaries
            """, re.X)
    f_re = re.compile(r"""
            # Make sure it's either at the beginning of a word, beginning of the
            # line, or at least not proceeded by an alphanumeric character
            (?: \A | \b | [ ] )
            (
                -? # optional minus
                \d+ # Capture a number
            )
            [ ]? # Optional space
            (?: degrees[ ] )? # An optional "degrees " spelled out
            (?: ° )? # An optional degrees sign would go here if we got unicode
            F # Capital F
            \b # only capture at word boundaries
            """, re.X)

    @Plugin.queued
    def handle_incoming(self, chans, name, msg, direct, reply):
        c_matches = self.c_re.findall(msg)
        f_matches = self.f_re.findall(msg)

        if c_matches and not f_matches:
            # Convert the given C to F
            replies = []
            for c in c_matches:
                c = int(c)
                f = (c * 9 / 5) + 32
                f = int(round(f))

                replies.append("%dC is %dF" % (c, f))

            reply("(btw: " + ", ".join(replies) + ")")

        elif f_matches and not c_matches:
            # Convert the given F to C
            replies = []
            for f in f_matches:
                f = int(f)
                c = (f - 32) * 5 / 9
                c = int(round(c))

                replies.append("%dF is %dC" % (f, c))

            reply("(btw: " + ", ".join(replies) + ")")
