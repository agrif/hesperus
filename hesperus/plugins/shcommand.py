from hesperus.plugin import CommandPlugin
from ..core import ConfigurationError, ET
from ..shorturl import short_url

import subprocess
from shlex import split as sh_split
from pipes import quote as sh_quote

def multiline(s):
    return " ".join(s.splitlines())

filters = {'shorturl' : short_url, 'multiline' : multiline}

def check_output(*args, **kwargs):
    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT
    # will hang for HUGE output... you were warned
    p = subprocess.Popen(*args, **kwargs)
    returncode = p.wait()
    if returncode:
        raise subprocess.CalledProcessError(returncode, args)
    return p.communicate()[0]

class ShCommandPlugin(CommandPlugin):
    @CommandPlugin.config_types(commands = ET.Element)
    def __init__(self, core, commands=None):
        super(CommandPlugin, self).__init__(core)
        
        self.commands = {}
        
        if commands == None:
            commands = []
        for el in commands:
            if not el.tag.lower() == 'command':
                raise ConfigurationError('commands must contain command tags')
            name = el.get('name', None)
            if name == None:
                raise ConfigurationError('command tags must have a name')
            filt = el.get('filter', None)
            if filt and not filt in filters:
                raise ConfigurationError('invalid command filter')
            if filt:
                filt = filters[filt]
            else:
                filt = lambda s: s
            error = el.get('error', 'command failed')
            command = el.text.strip()
            
            self.commands[name.lower()] = (command, filt, error)
        
    @CommandPlugin.register_command(r"(\S+)(?:\s+(.+))?")
    def run_command(self, chans, name, match, direct, reply):
        cmd = match.group(1).lower()
        if not cmd in self.commands:
            return

        cmd, filt, error = self.commands[cmd]
        args = match.group(2)
        if not args:
            args = ""
        
        try:
            args = map(sh_quote, sh_split(args))
            args = " " + " ".join(args)
        except ValueError:
            self.log_error("invalid arguments for \"%s\"" % (match.group(1),))
            reply(error)
            return
        
        try:
            output = check_output(cmd + args, shell=True)
            output = filt(output)
            reply(output)
        except subprocess.CalledProcessError:
            self.log_error("could not run command \"%s\"" % (match.group(1),))
            reply(error)
