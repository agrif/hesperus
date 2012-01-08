import subprocess

from ..plugin import PassivePlugin, CommandPlugin

class RunACommand(PassivePlugin, CommandPlugin):
    """Runs a command and interactively accepts input.

    This plugin DOES NOT WORK. I hacked it up in about 20 minutes. I think the
    problem is the blocking run() method while calling readlines().

    """

    # This is necessary because the run() method blocks waiting for input
    commands_queued = False

    def __init__(self, core):
        super(RunACommand, self).__init__(core)

        self.process = None
        self.outputbuf = ""

    @CommandPlugin.register_command("run (.*)")
    def starttheprogram(self, chans, name, match, direct, reply):
        if self.process:
            self.log_debug("Terminating existing process")
            self.process.terminate()
            self.process.wait()

        self.process = subprocess.Popen(match.group(1), shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.parent.send_outgoing("default", "Running the command. Prefix input with @")
        self.log_debug("Launched process: %s" % self.process)

    @CommandPlugin.register_command("stop")
    def stoptheprogram(self, chans, name, match, direct, reply):
        p = self.process
        if p:
            self.process = None
            self.log_debug("Terminating the current process...")
            p.terminate()
            p.wait()
            self.log_debug("Terminated")

    def run(self):
        while True:
            yield
            p = self.process
            if p:
                # Check stdout for output
                line = p.stdout.readline()
                if not line:
                    self.process = None
                    self.log_debug("Got a blank line from subprocess. wait()ing it")
                    p.wait()
                    self.parent.send_outgoing("deafult", "Process ended")
                else:
                    self.log_debug("Got a line from the subprocess: %r", line)
                    self.parent.send_outgoing("default", "cmd output: %s" % line.rstrip())

    @PassivePlugin.register_pattern("^@(.*)")
    def cmdinput(self, match, reply):
        p = self.process
        if p:
            self.log_debug("Got a line %r. Sending to process %s" % (match.group(1), p))
            p.stdin.write(match.group(1) + "\n")
            p.stdin.flush()
