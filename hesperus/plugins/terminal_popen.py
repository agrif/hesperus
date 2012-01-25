import StringIO
import pty
import os
import subprocess
import termios
import fcntl
import errno

def postfork():
    """This is executed in the forked child, before it executes the requested
    program
    
    """
    # Become a session leader by creating a new session. This detaches us from
    # the previous controlling terminal
    os.setsid()
    
    # Now use the TIOCSCTTY ioctl to set our controlling terminal to whatever
    # stdout is (the pty created earlier)
    fcntl.ioctl(1, termios.TIOCSCTTY)

# These options taken from a gnome-terminal session.
default_term_settings = [27906, 5, 1215, 35387, 15, 15, ['\x03', '\x1c',
        '\x7f', '\x15', '\x04', '\x00', '\x01', '\xff', '\x11', '\x13', '\x1a',
        '\xff', '\x12', '\x0f', '\x17', '\x16', '\xff', '\x00', '\x00', '\x00',
        '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
        '\x00', '\x00', '\x00']]


class TOpen(object):
    """Opens a subprocess in a pseudo terminal. The subprocess will think it's
    connected to a terminal and act accordingly.
    
    provides a simple line-oriented interface for reading and writing to the
    process. Reads are non-blocking.
    
    """
    def __init__(self, procstring):
        # Create a new pseudo-terminal pair. We'll read from the master side and
        # connect the child to the slave side.
        master, slave = pty.openpty()
    
        # Set terminal options to a typical interactive terminal, but with echo
        # turned off.
        settings = list(default_term_settings)
        settings[3] &= ~termios.ECHO
        termios.tcsetattr(slave, termios.TCSANOW, settings)

        self.proc = subprocess.Popen(procstring, shell=True,
                stdin=slave, stdout=slave, stderr=slave, close_fds=True,
                preexec_fn=postfork)
        os.close(slave)
        
        # Set it to non-blocking
        fl = fcntl.fcntl(master, fcntl.F_GETFL)
        fcntl.fcntl(master, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
        self.master = master

    def __del__(self):
        try:
            self.proc.terminate()
            self.proc.kill()
            self.proc.wait()
        except OSError:
            # If proc is already dead, this will raise an OSError.
            pass
        os.close(self.master)

    def is_terminated(self):
        return self.proc.poll() != None
    
    def terminate(self):
        self.proc.terminate()
        
    def kill(self):
        self.proc.kill()
    
    def get_line(self):
        """Returns a line of input from the process's stdout, not including the
        terminating newline. May return an empty string indicating no data
        
        """
        buf = StringIO.StringIO()

        # Read until a newline or no data or would block
        while True:
            try:
                a = os.read(self.master, 1)
            except OSError, e:
                if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    # Non-blocking read would block. Ignore.
                    break
                elif e.errno == errno.EIO:
                    # This can happen if the process ends and there's no more data
                    if self.is_terminated():
                        break
                    else:
                        raise
                else:
                    raise

            if not a or a == "\n":
                break

            buf.write(a)
            
        return buf.getvalue().rstrip("\r\n")
    
    def put_line(self, line):
        """Writes a line of text to the process's stdin. If the given string
        does not contain a newline, one will be provded for you.
        
        """
        if not line.endswith("\n"):
            line = line + "\n"
        r = os.write(self.master, line)
        if r != len(line):
            # TODO: fix this possibility
            print "Warning: %s bytes of %r written" % (r, line)

