from ..plugin import PassivePlugin
import socket
from time import time

class IpCheckerPlugin(PassivePlugin):
    _recent_ips = {}
    @PassivePlugin.register_pattern(r'\b((?:\d{1,3}\.){3}\d{1,3})\b')
    def check_ip(self, match, reply):
        ip = match.group(1)
        now = int(time())
        if ip in self._recent_ips && now - self._recent_ips[ip] > 15:
            try:
                (host, _, _) = socket.gethostbyaddr(ip)
            except Exception as err:
                self.log_warning(err)
            else:
                reply('btw: {ip} maps back to "{host}"'.format(ip=ip, host=host))
                self._recent_ips[ip] = now
