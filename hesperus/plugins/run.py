import string
import random
import time

from ..plugin import PassivePlugin, CommandPlugin

import terminal_popen

class RunACommand(PassivePlugin, CommandPlugin):
    """Runs a command and interactively accepts input.

    This command now works, but is TOTALLY INSECURE! Also, it uses psuedo
    terminals to fool the subprocess into thinking it's attached to a terminal.
    Don't try running any curses apps or apps with color. That might not work
    too well. TODO: Strip out all control characters, or set the terminal
    settings something more appropriate (that doesn't include ANY
    non-line-oriented things like moving the cursor)

    """

    @CommandPlugin.config_types(replychannel = str)
    def __init__(self, core, replychannel):
        super(RunACommand, self).__init__(core)

        # Set to a SP object when a command is running.
        self.cmd = None
        self.channel = replychannel
        self.reply = None

        # Maps access strings to a tuple (cmdname, replyfunc)
        self.pendings = {}

    def _stopproc(self):
        with self.lock:
            p = self.cmd
            self.cmd = None
        if p:
            self.log_debug("Terminating existing process")
            p.terminate()
            time.sleep(0.1)
            while not p.is_terminated():
                time.sleep(1)
                p.kill()

    @CommandPlugin.register_command("run (.*)")
    def starttheprogram(self, chans, name, match, direct, reply):
        passcode = "".join(random.choice(string.ascii_lowercase) for _ in range(4))
        cmd = match.group(1)
        self.log_message("PM me the string %r if you want me to run %r" % (passcode, cmd))

        with self.lock:
            self.pendings[passcode] = (cmd, reply)

    @CommandPlugin.register_command("(\w+)")
    def approve(self, chans, name, match, direct, reply):
        msg = match.group(1)
        with self.lock:
            if direct and msg in self.pendings:
                cmdstr, origreply = self.pendings.pop(msg)
                self._startproc(cmdstr, origreply)

    @CommandPlugin.queued
    def _startproc(self, cmdstring, reply):
        if self.cmd:
            self._stopproc()

        cmd = terminal_popen.TOpen(cmdstring)
        with self.lock:
            self.cmd = cmd
        self.reply = reply

        reply("Running %r. Prefix input with @" % cmdstring)
        self.log_debug("Launched process: %s" % self.cmd)

    @CommandPlugin.register_command("terminate")
    def stoptheprogram(self, chans, name, match, direct, reply):
        p = self.cmd
        if p:
            self.log_debug("Terminating the current process...")
            reply("Stopping the process")
            self._stopproc()
            self.log_debug("Terminated")

    def run(self):
        while True:
            yield
            reply = self.reply
            p = self.cmd
            if p:
                # Check stdout for output
                line = p.get_line()
                if line.strip():
                    self.log_debug("Got a line from the subprocess: %r" % line)
                    self.parent.send_outgoing(self.channel, "output: %s" % line.rstrip())
                else:
                    # Check if process has ended. But only if there was no
                    # input, since there could still be data in the pipes
                    if p.is_terminated():
                        reply("Process ended")
                        with self.lock:
                            # Acquire the lock just in case a new proc gets set
                            # right now
                            if self.cmd is p:
                                self.cmd = None

                yield


    @PassivePlugin.register_pattern("^@(.*)")
    def cmdinput(self, match, reply):
        p = self.cmd
        if p:
            self.log_debug("Got a line %r. Sending to process %s" % (match.group(1), p))
            p.put_line(match.group(1))
