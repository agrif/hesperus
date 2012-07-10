from ..plugin import PassivePlugin
import socket

class IpCheckerPlugin(PassivePlugin):
    @PassivePlugin.register_pattern(r'\b((?:\d{1,3}\.){3}\d{1,3})\b')
    def check_ip(self, match, reply):
        ip = match.group(1)
        try:
            (host, _, _) = socket.gethostbyaddr(ip)
        except Exception as err:
            self.log_warning(err)
        else:
            reply('btw: {ip} maps back to "{host}"'.format(ip=ip, host=host))
