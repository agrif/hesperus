import threading
import time
from Queue import Queue
from traceback import format_exc
from ansi import colored

class Agent(object):
    stdout_lock = threading.RLock()
    
    def __init__(self, daemon=False):
        self.lock = threading.RLock()
        self._running = False
        self._error = None
        self._thread = None
        self._daemon = daemon
        self.queue = Queue(1000)
    
    # decorator to force a function to execute in the Agent's thread
    @classmethod
    def queued(cls, func):
        def queued_intern(self, *args, **kwargs):
            with self.lock:
                if threading.current_thread() == self.thread:
                    func(self, *args, **kwargs)
                    return
            self.queue.put((func, args, kwargs), True)
        return queued_intern
    
    @property
    def running(self):
        with self.lock:
            return self._running
    
    @property
    def error(self):
        with self.lock:
            return self._error
    
    @property
    def thread(self):
        with self.lock:
            return self._thread
    
    # override this in a subclass and yield every once in a while
    def run(self):
        while True:
            yield
        
    def start(self):
        with self.lock:
            self._running = True
            self._error = None
        
        self.log_debug("starting...")
        
        try:
            it = self.run()
            while True:
                try:
                    it.next()
                except StopIteration:
                    break

                with self.lock:
                    if not self._running:
                        break
                
                # give a little leeway
                time.sleep(0.1)

                while not self.queue.empty():
                    item = self.queue.get()
                    item[0](self, *item[1], **item[2])
        
        except Exception, e:
            with self.lock:
                self._error = (e, format_exc())
                if self._thread == None:
                    raise
        finally:
            self.log_debug("stopping...")
            with self.lock:
                self._running = False
                self._thread = None

    def start_threaded(self):
        self._thread = threading.Thread(target=self.start)
        self._thread.daemon = self._daemon
        self._thread.start()
        # wait until _running is true
        while not self.running:
            time.sleep(0.1)
    
    def stop(self):
        with self.lock:
            self._running = False

    def log(self, level, *message):
        global stdout_lock
        cls = self.__class__
        
        levels = [
            lambda s: colored('debug: ' + s, 'bold', 'black'),
            lambda s: colored(s, 'white'),
            lambda s: colored(s, 'bold', 'white'),
            lambda s: colored('warning', 'bold', 'yellow') + ': ' + colored(s, 'yellow'),
            lambda s: colored('error', 'bold', 'red') + ': ' + colored(s, 'red'),
        ]
        
        timebuf = time.strftime("%x %X")
        domain = cls.__module__
        if domain.startswith('hesperus.'):
            domain = domain.split('.', 1)[1]
        else:
            domain = 'extern.' + domain
        prefix = '(%s) [%s]' % (colored(timebuf, 'bold', 'blue'), colored(domain, 'cyan'))
        
        msg = levels[level](' '.join(map(str, message)))
        
        with cls.stdout_lock:
            print prefix, msg
    
    # conveniences for logging
    def log_debug(self, *msg): self.log(0, *msg)
    def log_verbose(self, *msg): self.log(1, *msg)
    def log_message(self, *msg): self.log(2, *msg)
    def log_warning(self, *msg): self.log(3, *msg)
    def log_error(self, *msg): self.log(4, *msg)
