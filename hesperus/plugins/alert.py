import time

from .plugin import CommandPlugin, PassivePlugin
from data247.api import ApiConnection

class SMSAlerter(CommandPlugin, PassivePlugin):
    @CommandPlugin.config_types(api_user=str, api_pass=str, timeout=int)
    def __init__(self, core, api_user, api_pass, timeout=900):
        super(SMSAlerter, self).__init__(core)
        self._data = {}
        self.api = ApiConnection(api_user, api_pass)
        self.timeout = timeout

    @CommandPlugin.register_command(r'smsalert\s+(\d+)')
    def alert_command(self, chans, name, msg, direct, reply):
        pass

    @PassivePlugin.register_pattern(r'(\w+)[:,]\s+(.+)')
    def ping_message(self, chans, name, msg, direct, reply):
        target = match.group(1)
        target_msg = match.group(2)
        now = int(time.time())
        if target in self._data.keys():
            if self._data[target]['enabled'] and \
                now - self._data[target]['last_active'] > self.timeout:
                self.notify(name, target, target_msg)

    @PassivePlugin.register_pattern(r'', True):
    def activity_watch(self, chans, name, msg, direct, reply):
        if name in self._data.keys():
            self._data[name]['last_active'] = int(time.time())

    def notify(self, src, dest, msg):
        pass
