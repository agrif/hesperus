from ..plugin import PollPlugin
import requests

class MojangStatus(PollPlugin):
    #STATUS_URL = 'http://status.mojang.com/check'
    STATUS_URL = 'http://waysaboutstuff.com/check.json'
    poll_interval = 15
    _last_status = None
    
    def poll(self):
        new_status = self._get_current_status()
        if self._last_status is not None:
            for (server, status) in self._last_status.iteritems():
                if status != new_status[server]:
                    self._send_output(server, status, new_status[server])
        self._last_status = new_status
    
    def _send_output(server, old_status, new_status):
        msg = 'Mojang server {server} changed status from "{old}" to "{new}"'.format(
            server=server,
            old=old_status,
            new=new_status)
        for chan in self.channels:
            self.parent.send_outgoing(msg)
    
    def _get_current_status(self):
        status_json = requests.get(self.STATUS_URL).json
        status = {}
        for element in status_json:
            key, value = next(element.iteritems())
            status[key] = value
        return status
