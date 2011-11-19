import hashlib
import urllib
import json
import socket

from ..core import ConfigurationError
from ..plugin import Plugin, PollPlugin

class Transport(object):
    def call(self, name, args):
        raise NotImplementedError("call")

class DebugTransport(Transport):
    def call(self, name, args):
        print name, args
        return 0

class SocketJSONTransport(Transport):
    def __init__(self, server, port, username, password, salt):
        super(SocketJSONTransport, self).__init__()
        self._server = server
        self._port = port
        self._user = username
        self._passwd = password
        self._salt = salt
        self._subscriptions = {}
        self._reopen()

    def _reopen(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self._server, self._port))
        self._file = self._sock.makefile("rb")
        
        subscriptions = self._subscriptions
        self._subscriptions = {}
        for name, func in subscriptions.iteritems():
            self.subscribe(name, func)
    
    def _genKey(self, methname):
        key = self._user + methname + self._passwd + self._salt
        return hashlib.sha256(key).hexdigest()
    
    def call(self, name, args):
        data = {'method' : name, 'key' : self._genKey(name)}
        if args:
            data['args'] = json.dumps(args)
        url = "/api/call?" + urllib.urlencode(data)
        
        self._sock.send(url + '\n')
        while True:
            res = self._file.readline()
            res = json.loads(res)
            
            if res['source'] == name:
                break
            
            # handle what *must* be a subscription
            if not res['source'] in self._subscriptions:
                raise RuntimeError('message from unsubscribed source')
            func = self._subscriptions[res['source']]
            func(res['success'])
        
        return res['success']
    
    def subscribe(self, name, func):
        if not name in self._subscriptions:
            data = {'source' : name, 'key' : self._genKey(name)}
            url = "/api/subscribe?" + urllib.urlencode(data)
            self._sock.send(url + '\n')
        self._subscriptions[name] = func
        self.flush()
    
    def flush(self):
        # force a function call that's really used to find the end-of-messages
        # this is a hack. sorry!
        self.call('getServerPort', ())

_endpoints = []
class EndpointMetaclass(type):
    def __new__(cls, name, bases, dct):
        namespace = dct.get('namespace', None)
        
        for methname in dct:
            if methname.startswith('_') or methname == 'namespace':
                continue
            
            res, args = dct[methname]
            def make_call(namespace, methname, restype, argtypes):
                def call(self, *args):
                    if not len(args) == len(argtypes):
                        if len(argtypes) == 1:
                            raise TypeError("%s() takes exactly 1 argument (%i given)" % (methname, len(args)))
                        raise TypeError("%s() takes exactly %i arguments (%i given)" % (methname, len(argtypes), len(args)))
                    
                    converted_args = []
                    for i, (val, convert) in enumerate(zip(args, argtypes)):
                        try:
                            converted_args.append(convert(val))
                        except (ValueError, TypeError), e:
                            raise TypeError("argument %i: %s" % (i, str(e)))
                    
                    fullmeth = methname
                    if namespace:
                        fullmeth = namespace + '.' + fullmeth
                    res = self._trans.call(fullmeth, converted_args)
                    
                    if not res and not restype:
                        return None
                    
                    try:
                        return restype(res)
                    except (ValueError, TypeError):
                        raise RuntimeError("could not convert return value")
                
                call.func_name = methname
                call._prototype_ = (restype, argtypes)
                return call
            dct[methname] = make_call(namespace, methname, res, args)
        
        endpoint = super(EndpointMetaclass, cls).__new__(cls, name, bases, dct)
        
        global _endpoints
        _endpoints.append(endpoint)
        return endpoint

class Endpoint(object):
    __metaclass__ = EndpointMetaclass
    namespace = None
    def __init__(self, transport):
        super(Endpoint, self).__init__()
        self._trans = transport

class Bukkit(object):
    def __init__(self, *args, **kwargs):
        super(Bukkit, self).__init__()
        transport = kwargs.pop('trasport', SocketJSONTransport)
        
        self._trans = transport(*args, **kwargs)
        
        global _endpoints
        for cls in _endpoints:
            if cls == Endpoint:
                continue
            ep = cls(self._trans)
            namespace = ep.namespace
            if not namespace:
                namespace = "_default"
            if namespace in dir(self):
                raise RuntimeError("namespace '%s' registered more than once" % (namespace,))
            setattr(self, namespace, ep)
        
        # set up the proxy functions for the default namespace
        for methname in dir(self._default):
            if methname.startswith('_') or methname == 'namespace':
                continue
            def make_proxy(endpoint, methname):
                def proxy(*args):
                    return getattr(endpoint, methname)(*args)
                proxy.func_name = methname
                return proxy
            setattr(self, methname, make_proxy(self._default, methname))
    
    def subscribe(self, *args):
        return self._trans.subscribe(*args)
    def flush(self, *args):
        return self._trans.flush(*args)

# types are conversion functions
INT = int
STRING = str
BOOLEAN = bool
OBJECT = lambda o: o

class DefaultEndpoint(Endpoint):
    addToWhitelist = (None, (STRING))
    ban = (None, (STRING))
    banIP = (None, (STRING))
    broadcast = (INT, (STRING))
    broadcastWithName = (BOOLEAN, (STRING, STRING))
    clearPlayerInventorySlot = (BOOLEAN, (STRING, INT))
    deopPlayer = (None, (STRING))
    disablePlugin = (BOOLEAN, (STRING))
    disablePlugins = (None, ())
    editPropertiesFile = (BOOLEAN, (STRING, STRING, STRING, STRING))
    enablePlugin = (BOOLEAN, (STRING))
    getBannedIPs = (OBJECT, ())
    getBannedPlayers = (OBJECT, ())
    getDirectory = (OBJECT, (STRING))
    getFileContents = (STRING, (STRING))
    getLatestChats = (OBJECT, ())
    getLatestChatsWithLimit = (OBJECT, (INT))
    getLatestConnections = (OBJECT, ())
    getLatestConnectionsWithLimit = (OBJECT, (INT))
    getLatestConsoleLogs = (OBJECT, ())
    getLatestConsoleLogsWithLimit = (OBJECT, (INT))
    getPlayer = (OBJECT, (STRING))
    getPlayerCount = (INT, ())
    getPlayerLimit = (INT, ())
    getPlayers = (OBJECT, ())
    getPlugin = (OBJECT, (STRING))
    getPluginFiles = (OBJECT, (STRING))
    getPlugins = (OBJECT, ())
    getPropertiesFile = (OBJECT, (STRING))
    getServer = (OBJECT, ())
    getServerIp = (STRING, ())
    getServerPort = (INT, ())
    getServerVersion = (STRING, ())
    getStream = (OBJECT, (STRING))
    getStreamWithLimit = (OBJECT, (STRING, INT))
    getWhitelist = (OBJECT, ())
    getWorld = (OBJECT, (STRING))
    getWorlds = (OBJECT, ())
    givePlayerItem = (BOOLEAN, (STRING, INT, INT))
    givePlayerItemDrop = (BOOLEAN, (STRING, INT, INT))
    givePlayerItemDropWithData = (BOOLEAN, (STRING, INT, INT, INT))
    givePlayerItemWithData = (BOOLEAN, (STRING, INT, INT, INT))
    kickPlayer = (None, (STRING, STRING))
    opPlayer = (None, (STRING))
    reloadServer = (None, ())
    removeFromWhitelist = (None, (STRING))
    removePlayerInventoryItem = (OBJECT, (STRING, INT))
    runConsoleCommand = (None, (STRING))
    saveMap = (None, ())
    saveOff = (None, ())
    saveOn = (None, ())
    sendMessage = (None, (STRING, STRING))
    setFileContents = (BOOLEAN, (STRING, STRING))
    setPlayerHealth = (BOOLEAN, (STRING, INT))
    setPlayerInventorySlot = (BOOLEAN, (STRING, INT, INT, INT))
    setPlayerInventorySlotWithDamage = (BOOLEAN, (STRING, INT, INT, INT, INT))
    setPlayerInventorySlotWithData = (BOOLEAN, (STRING, INT, INT, INT, INT))
    setPlayerInventorySlotWithDataAndDamage = (BOOLEAN, (STRING, INT, INT, INT, INT, INT))
    teleport = (None, (STRING, STRING))
    unban = (None, (STRING))
    unbanIP = (None, (STRING))
    updatePlayerInventorySlot = (BOOLEAN, (STRING, INT, INT))

class DynmapEndpoint(Endpoint):
    namespace = "dynmap"
    
    getHost = (STRING, ())
    getPort = (STRING, ())

class RemoteToolkitEndpoint(Endpoint):
    namespace = "remotetoolkit"
    
    rescheduleServerRestart = (BOOLEAN, (STRING))
    restartServer = (BOOLEAN, ())
    startServer = (BOOLEAN, ())
    stopServer = (BOOLEAN, ())

class SystemEndpoint(Endpoint):
    namespace = "system"
    
    getDiskFreeSpace = (INT, ())
    getDiskSize = (INT, ())
    getDiskUsage = (INT, ())
    getJavaMemoryTotal = (INT, ())
    getJavaMemoryUsage = (INT, ())

class BukkitPlugin(PollPlugin):
    poll_interval = 2
    
    @Plugin.config_types(server=str, port=int, username=str, password=str, salt=str)
    def __init__(self, core, server='localhost', port=20060, username='hesperus', password='', salt=''):
        super(BukkitPlugin, self).__init__(core)
        
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.salt = salt
        
        self.b = Bukkit(server, port, username, password, salt)
        self.ignore = True
        self.b.subscribe('chat', self._handle)
        self.ignore = False
    
    def poll(self):
        self.b.flush()
        yield
    
    def _handle(self, it):
        if self.ignore:
            return
        nick = it['player'].encode()
        msg = it['message'].encode()
        
        # ignore our own messages
        if nick == self.username:
            return
        
        def reply(msg):
            self.b.broadcastWithName(msg, self.username)
        self.parent.handle_incoming(self.channels, nick, msg, False, reply)

    def send_outgoing(self, chan, msg):
        self.b.broadcastWithName(msg, self.username)
