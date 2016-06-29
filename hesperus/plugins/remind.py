from hesperus.plugin import CommandPlugin, PersistentPlugin
import time
import re

class RemindPlugin(CommandPlugin, PersistentPlugin):
    _USAGE = 'usage: remind <username> <message> ' \
        '[in|at|for <timespec>]'
    # haha suck it agrif
    FIBONACCI_SEQ = [i * 60*60*24 for i in \
        [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584]
    ]

    compres = [
              re.compile(r"^in (?P<timespec>(\d+ \w+?s? ?)+) (?P<action>.*?)$"),
              re.compile(r"^(?P<action>.*) in (?P<timespec>(\d+ \w+?s? ?)+)$"),
              ]

    atres = [
            re.compile(r"^at (?P<month>\w{3,4})[-/ ](?P<day>\d\d?)[-/ ](?P<year>\d{4})\D(?P<hour>\d\d?)\D(?P<min>\d\d)\D(?P<sec>\d\d) (?P<action>.*?)$"),
            re.compile(r"^at (?P<year>\d{4})[-/ ](?P<month>\w{3,4})[-/ ](?P<day>\d\d?)\D(?P<hour>\d\d?)\D(?P<min>\d\d)\D(?P<sec>\d\d) (?P<action>.*?)$"),
            re.compile(r"^at (?P<year>\d{4})[-/ ](?P<day>\d\d?)[-/ ](?P<month>\w{3,4})\D(?P<hour>\d\d?)\D(?P<min>\d\d)\D(?P<sec>\d\d) (?P<action>.*?)$"),
            re.compile(r"^at (?P<day>\d\d?)[-/ ](?P<month>\w{3,4})[-/ ](?P<year>\d{4})\D(?P<hour>\d\d?)\D(?P<min>\d\d)\D(?P<sec>\d\d) (?P<action>.*?)$"),
            re.compile(r"^(?P<action>.*?) at (?P<month>\w{3,4})[-/ ](?P<day>\d\d?)[-/ ](?P<year>\d{4})\D(?P<hour>\d\d?)\D(?P<min>\d\d)\D(?P<sec>\d\d)$"),
            re.compile(r"^(?P<action>.*?) at (?P<year>\d{4})[-/ ](?P<month>\w{3,4})[-/ ](?P<day>\d\d?)\D(?P<hour>\d\d?)\D(?P<min>\d\d)\D(?P<sec>\d\d)$"),
            re.compile(r"^(?P<action>.*?) at (?P<year>\d{4})[-/ ](?P<day>\d\d?)[-/ ](?P<month>\w{3,4})\D(?P<hour>\d\d?)\D(?P<min>\d\d)\D(?P<sec>\d\d)$"),
            re.compile(r"^(?P<action>.*?) at (?P<day>\d\d?)[-/ ](?P<month>\w{3,4})[-/ ](?P<year>\d{4})\D(?P<hour>\d\d?)\D(?P<min>\d\d)\D(?P<sec>\d\d)$")
            ]

    forres = [
        re.compile(r'(?P<action>.*) for (?P<timespec>(\d+ \w+?s? ?)+)$'),
        re.compile(r"^for (?P<timespec>(\d+ \w+?s? ?)+) (?P<action>.*?)$"),
    ]

    unit_map = {
        "second": 1,
        "sec": 1,
        "min": 60,
        "minute": 60,
        "hour": 60*60,
        "hr": 60*60,
        "day": 60*60*24,
        "week": 60*60*24*7,
        "wk": 60*60*24*7,
        "month": 60*60*24*30,
        "year": 60*60*24*365,
    }

    persistence_file = 'remind.json'
    @CommandPlugin.config_types(min_delay=int)
    def __init__(self, core, min_delay=300):
        super(RemindPlugin, self).__init__(core)
        self._min_delay = min_delay
        self.load_data()

    @CommandPlugin.register_command(r"remind(?:\s+(?P<target>[^ ]+))?(?:\s+(?P<message_with_timespec>.*?))?")
    def remind_command(self, chans, name, match, direct, reply):
        parts = match.groupdict()
        self.log_debug(match.group(0) + repr(match.groupdict()))
        if not parts['target'] or not parts['message_with_timespec']:
            reply(self._USAGE)
            return
        if parts['target'].lower() == 'me':
            parts['target'] = name

        if self._add_notice(source=name, **parts):
            reply('Reminder for {} saved.'.format(parts['target']))
        else:
            reply('Reminder not saved, use a longer delay (min is %d seconds).' % self._min_delay)

    @CommandPlugin.register_command(r'reminders')
    def reminders_command(self, chans, name, match, direct, reply):
        reply(repr(self._data))

    def _add_notice(self, source, target, message_with_timespec):
        target = target.lower()
        if target not in self._data:
            self._data[target] = []
        now = int(time.time())

        delay, message = self._parse_and_extract(message_with_timespec)
        if delay is not None and delay < 0:
            delay = abs(delay + now)
            for d in self.FIBONACCI_SEQ:
                if d < delay:
                    self._data[target].append({
                        'target': target,
                        'source': source,
                        'message': message,
                        'time': now,
                        'delay': d,
                    })
                else:
                    break
            self._data[target].append({
                'target': target,
                'source': source,
                'message': message,
                'time': now,
                'delay': d,
            })
        else:
            if delay is None:
                delay = self._min_delay
            else:
                delay = delay - now

            self._data[target].append({
                'target': target,
                'source': source,
                'message': message,
                'time': now,
                'delay': delay,
            })
        self.save_data()
        return True

    def _parse_and_extract(self, string):
        now = int(time.time())
        for regex in self.forres:
            m = regex.match(string)
            if m:
                timespec = m.group('timespec').split(' ')
                action = m.group('action')
                val = 0
                for x in range(0, len(timespec), 2):
                    num = int(timespec[x])
                    unit = timespec[x+1]
                    if unit.endswith("s"):
                        unit = unit[:-1]
                    val += self.unit_map[unit] * num
                return (-(now+val), action)

        for regex in self.compres:
            m = regex.match(string)
            if m:
                timespec = m.group("timespec").split(" ")
                action = m.group("action")
                val = 0
                for x in range(0, len(timespec), 2):
                    num = int(timespec[x])
                    unit = timespec[x+1]
                    if unit.endswith("s"):
                        unit = unit[:-1]
                    val += self.unit_map[unit] * num
                return (now+val, action)

        for regex in self.atres:
            m = regex.match(string)
            if m:
                ts = time.strptime("%s %s %s %s %s %s" % m.group("year", "month", "day", "hour", "min", "sec"),
                        "%Y %b %d %H %M %S")
                return int(time.mktime(ts)), m.group("action")

        # if still no match, assume no timespec
        return (None, string)

    @CommandPlugin.queued
    def remind_check(self, name, reply):
        now = int(time.time())
        name = name.lower()
        if name in self._data:
            to_del = []
            for i, notice in enumerate(self._data[name]):
                diff = now - notice['time']
                if diff >= notice['delay']:
                    w = diff / self.unit_map['week']
                    d = (diff % self.unit_map['week']) / self.unit_map['day']
                    h = (diff % self.unit_map['day']) / self.unit_map['hour']
                    m = (diff % self.unit_map['hour']) / self.unit_map['minute']

                    ago = '%02dm' % m                    
                    if h > 0:
                        ago = ('%02dh' % h) + ago
                    if d > 0:
                        ago = ('%02dd' % d) + ago
                    if w > 0:
                        ago = ('%02dw' % w) + ago

                    reply('{target}, {source} reminds you "{message}" ({ago} ago)'.format(
                        ago=ago, **notice))
                    to_del.append(i)
            if to_del:
                for i in to_del[::-1]:
                    try:
                        del self._data[name][i]
                    except IndexError:
                        self.log_warning('Failed to delete message #%d for %s' % (i, name))
                self.save_data()
            if not self._data[name]:
                del self._data[name]
                self.save_data()

    def handle_incoming(self, chans, name, msg, direct, reply):
        super(RemindPlugin, self).handle_incoming(chans, name, msg, direct, reply)
        if not direct:
            self.remind_check(name, reply)
