from ..plugin import PassivePlugin
import socket
from time import time

class IpCheckerPlugin(PassivePlugin):
    _recent_ips = {}
    
    @PassivePlugin.config_types(cooldown=int)
    def __init__(self, core, cooldown=60):
        super(IpCheckerPlugin, self).__init__(core)
        self._cooldown = cooldown

    @PassivePlugin.register_pattern(r'\b((?:\d{1,3}\.){3}\d{1,3})\b')
    def check_ip(self, match, reply):
        ip = match.group(1)
        now = int(time())
        if not self._ip_on_cooldown(ip) and \
                not any(ip.startswith(subnet) for subnet in ['127.', '10.', '192.168.', '172.']):
            try:
                (host, _, _) = socket.gethostbyaddr(ip)
            except Exception as err:
                self.log_warning(err)
            else:
                reply('btw: {ip} maps back to "{host}"'.format(ip=ip, host=host))
                self._recent_ips[ip] = now

    def _ip_on_cooldown(self, ip):
        return not (ip not in self._recent_ips or \
            (ip in self._recent_ips and int(time()) - self._recent_ips[ip] > self._cooldown))
