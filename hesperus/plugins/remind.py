from hesperus.plugin import CommandPlugin, PersistentPlugin
import time

class RemindPlugin(CommandPlugin, PersistentPlugin):
    _USAGE = 'usage: remind <username> [@delay[m|h|d]] <message> ' \
        '[in <delay> [minutes|hours|days]]'

    persistence_file = 'remind.json'
    @CommandPlugin.config_types(min_delay=int)
    def __init__(self, core, min_delay=300):
        super(RemindPlugin, self).__init__(core)
        self._min_delay = min_delay
        self.load_data()

    @CommandPlugin.register_command(r"remind(?:\s+(?P<target>.*?))?(?:\s+@(?P<time_spec>\d+[hmd]?))?(?:\s+(?P<message>.*?))?(?:\s+in\s+(?P<nat_time_spec>\d+\s+(?:mins?(?:utes?)?|hours?|days?)))?")
    def remind_command(self, chans, name, match, direct, reply):
        parts = match.groupdict()
        reply(repr(parts))
        if not parts['target'] or not parts['message']:
            reply(self._USAGE)

        if self._add_notice(source=name, **parts):
            reply('Reminder saved.')
        else:
            reply('Reminder not saved, use a longer delay.')

    def _add_notice(self, source, target, message, time_spec=None, nat_time_spec=None):
        if target not in self._data:
            self._data[target] = []
        now = int(time.time())
        if nat_time_spec or time_spec:
            delay = self._parse_natural_time(nat_time_spec) \
                if nat_time_spec else self._parse_time(time_spec)
            if delay < self._min_delay:
                return False
        else:
            delay = self._min_delay

        self._data[target].append({
            'target': target,
            'source': source,
            'message': message,
            'time': now,
            'delay': delay,
        })
        self.save_data()
        return True

    def _parse_natural_time(self, spec):
        ammount, unit = filter(None, (p.strip() for p in spec.split()))
        if unit.startswith('day'):
            return int(ammount) * 86400
        elif unit.startswith('hour'):
            return int(ammount) * 3600
        else:
            return int(ammount) * 60

    def _parse_time(self, spec):
        if spec.endswith('d'):
            return int(spec[:-1]) * 86400
        elif spec.endswith('h'):
            return int(spec[:-1]) * 3600
        else:
            if spec.endswith('m'):
                return int(spec[:-1]) * 60
            else:
                return int(spec) * 60

    @CommandPlugin.queued
    def remind_check(self, name, reply):
        if name in self._data:
            to_del = []
            for i, notice in enumerate(self._data[name]):
                if int(time.time()) > (notice['time'] + notice['delay']):
                    reply('{target}, {source} reminds you `{message}\' ({ago} seconds ago)'.format(
                        ago=(int(time.time())-notice['time']), **notice))
                    to_del.append(i)
            if to_del:
                for i in to_del:
                    del self._data[name][i]
                self.save_data()
            if not self._data[name]:
                del self._data[name]
                self.save_data()

    def handle_incoming(self, chans, name, msg, direct, reply):
        super(RemindPlugin, self).handle_incoming(chans, name, msg, direct, reply)
        if direct:
            return

        self.remind_check(name, reply)
