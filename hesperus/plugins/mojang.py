from ..plugin import PollPlugin
import requests
import json
import time

class MojangStatus(PollPlugin):
    STATUS_URL = 'http://status.mojang.com/check'
    GRACE_PERIOD = 120
    poll_interval = 30
    _last_status = None
    _watched = None
    
    def poll(self):
        if self._watched is None:
            self._watched = {}
        new_status = self._get_current_status()
        if new_status is not None:
            if self._last_status is not None:
                for (server, status) in self._last_status.iteritems():
                    if status != new_status[server]:
                        if server in self._watched:
                            self.log_debug('stopped watching status changed server: ' + server)
                            del self._watched[server]
                        else:
                            self.log_debug('watching mojang server: ' + server)
                            self._watched[server] = int(time.time())
                    else:
                        if server in self._watched and \
                                int(time.time()) - self._watched[server] > self.GRACE_PERIOD:
                            self._send_output(server, new_status[server])
                            del self._watched[server]
            self._last_status = new_status
        yield
    
    def _send_output(self, server, status):
        msg = 'Mojang server {server} changed status to "{status}"'.format(
            server=server,
            status=status)
        for chan in self.channels:
            self.parent.send_outgoing(chan, msg)
    
    def _get_current_status(self):
        try:
            status_json = json.loads(requests.get(self.STATUS_URL).text)
        except (requests.exceptions.ConnectionError, ValueError) as err:
            self.log_warning(err)
            return None
        return dict((server, status) for e in status_json for (server, status) in e.iteritems())
