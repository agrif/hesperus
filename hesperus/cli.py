from __future__ import print_function

import readline
import threading
import sys
import time

class UnknownCommand(Exception):
    pass

class CLI(object):
    ESC = chr(27)
    
    def __init__(self, ps1, ps2):
        self.ps1 = str(ps1) + " "
        self.ps2 = str(ps2) + " "
        self.lock = threading.RLock()
        self.prompting = False
    
    def print_line(self, *args):
        with self.lock:
            if self.prompting:
                # if we just started prompting, wait a bit
                if self.prompting_time + 0.1 < time.time():
                    time.sleep(0.1)
                # goto col 0, clear line
                sys.stdout.write(self.ESC + '[G' + self.ESC + '[2K')
                print(*args)
                print(self.prompt, readline.get_line_buffer(), sep='', end='')
                sys.stdout.flush()
            else:
                print(*args)
    
    def do_prompt(self, prompt):
        try:
            with self.lock:
                self.prompting_time = time.time()
                self.prompting = True
                self.prompt = prompt
                print(self.prompt, end='')
            cmd = str(raw_input())
        finally:
            with self.lock:
                self.prompting = False
        return cmd + '\n'
    
    def run_once(self):
        cmd = self.do_prompt(self.ps1)
        
        try:
            needs_more = self.handle_input(cmd)
            while needs_more:
                cmd += self.do_prompt(self.ps2)
                needs_more = self.handle_input(cmd)
        except UnknownCommand, e:
            self.handle_error(e)
    
    def run(self):
        while True:
            try:
                self.run_once()
            except (EOFError, KeyboardInterrupt), e:
                with self.lock:
                    self.prompting = False
                    self.print_line()
                break

        
    # either raise UnknownCommand, return True to read more
    # or return False to be done with it
    def handle_input(self, s):
        if len(s) < 5:
            return True
        elif len(s) == 6:
            raise UnknownCommand('this is a test')
        else:
            self.print_line(repr(s))
            return False
    
    # handle an UnkownCommand error
    def handle_error(self, e):
        self.print_line("unkown command:", e)
