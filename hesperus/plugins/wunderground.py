from wunderpython import wunderground

from .irc import IRCPlugin
from ..plugin import CommandPlugin
from ..shorturl import short_url

class WundergroundPlugin(CommandPlugin):

    REPLY_MESSAGE_FMT = u'Currently {c[temperature_string]} and {c[weather]} in {l.name}'

    @CommandPlugin.config_types(api_key=str, max_locations=int)
    def __init__(self, core, api_key=None, max_locations=3):
        super(WundergroundPlugin, self).__init__(core)
        self._api_key = api_key
        self._max_locs = max_locations
        
        self._conn = wunderground.Wunderground(self._api_key)
        self.log_debug('Init with api_key={} and max_locs={}'.format(api_key, max_locations))

    @CommandPlugin.register_command(r'w(?:under)?g(?:round)?\s+(.+)')
    def command_get_weather(self, chans, name, match, direct, reply):
        given_location = match.group(1)
        self.log_debug('Got location from IRC: {}'.format(given_location))
        wg_locations = self._get_locations(given_location)

        if wg_locations:
            for wg_loc in wg_locations:
                reply(self._format_message(wg_loc))
        else:
            reply('dunno where that is')

    def _get_locations(self, loc):
        return [self._conn[l.encode('ascii')] \
            for l in self._conn.search(loc)[:self._max_locs]]

    def _format_message(self, wg_loc):
        return self.REPLY_MESSAGE_FMT.format(l=wg_loc, c=wg_loc.conditions)
