import packagetrack
from packagetrack.carriers.errors import *
from packagetrack.configuration import DotFileConfig
import time
import datetime
import json
import random
import traceback
from ..plugin import PollPlugin, CommandPlugin
from ..shorturl import short_url
from .irc import IRCPlugin

class PackageTracker(CommandPlugin, PollPlugin):
    @CommandPlugin.config_types(persist_file=str, auth_file=str, retry_period=int)
    def __init__(self, core, persist_file='shipping-following.json', auth_file=None, retry_period=24):
        super(PackageTracker, self).__init__(core)
        self._persist_file = persist_file
        self._data = {}
        self._unready_data = {}
        self._retry_period = retry_period
        packagetrack.auto_register_carriers(DotFileConfig(auth_file))
        self.load_data()
        try:
            with open('/usr/share/dict/words', 'r') as words:
                self._word_database = [line.strip() for line in words \
                    if not any(str(i) in line for i in range(10)) and len(line) <= 9]
            self.log_debug('Found %d words for tag generation' % len(self._word_database))
        except IOError as err:
            self._word_database = None
            self.log_debug('Word database not loaded: %s' % err)

    @CommandPlugin.register_command(r"ptrack(?:\s+([\w\d]+))?(?:\s+(.+))?")
    def track_command(self, chans, name, match, direct, reply):
        if match.group(1):
            tn = match.group(1)
            if tn in self._data.keys():
                if name == self._data[tn]['owner'] or 'admin' in chans:
                    del self._data[tn]
                    self.save_data()
                    reply('WELL FINE THEN, I won\'t tell you about that package anymore')
                else:
                    reply('You can\'t tell me what to do, you\'re not even my real dad!')
            else:
                package = self.get_package(tn)
                try:
                    state = package.track()
                except TrackingNumberFailure:
                    reply('{carrier} doesn\'t have any info on that number'.format(
                        carrier=package.carrier))
                except UnsupportedTrackingNumber:
                    self.log_warning('bad tracking number: {0}'.format(tn))
                    reply('I don\'t know how to deal with that number')
                except TrackingFailure as err:
                    data = {
                        'tag': match.group(2) if match.group(2) else self._generate_tag(tn),
                        'owner': name,
                        'channels': chans,
                        'direct': direct,
                        'last_update': int(time.time())
                    }
                    self._unready_data[tn] = data
                    self.log_debug('Unready package: %s' % err)
                    reply('{p.carrier} doesn\'t know about "{d[tag]}" yet but I\'ll keep an eye on it ' \
                        'for {0} hours and let you know if they find it'.format(
                            self._retry_period, p=package, d=data))
                else:
                    if state.is_delivered:
                        reply('Go check outside, that package has already been delivered: <%s>' % short_url(package.url))
                    else:
                        data = {
                            'tag': match.group(2) if match.group(2) else self._generate_tag(tn),
                            'owner': name,
                            'channels': chans,
                            'direct': direct,
                            'last_update': int(time.mktime(state.last_update.timetuple()))
                        }
                        self._data[tn] = data
                        self.save_data()
                        reply('"{tag}" is at "{state}" now, I\'ll let you know when it changes'.format(
                            state=state.status, tag=data['tag']))
        else:
            packages = [self.get_package(tn) for tn in self._data.keys() if self._data[tn]['owner'] == name]
            if packages:
                for package in packages:
                    self.output_status(package)
            else:
                reply('I\'m not watching any packages for you right now')

    def poll(self):
        expired = {}
        found = {}
        for (tn, data) in self._unready_data.items():
            package = self.get_package(tn)
            try:
                new_state = package.track()
            except TrackingFailure as e:
                if int(time.time()) - data['last_update'] > self._retry_period * 3600:
                    expired[tn] = data
            else:
                found[tn] = data
            yield
        for (tn, data) in found.items():
            package = self.get_package(tn)
            self._raw_message(None,
                '{d[owner]}: {p.carrier} seems to have found your "{d[tag]}", I\'ll watch it for updates now'.format(
                    d=data, p=package))
            self._data[tn] = data
            del self._unready_data[tn]
        for (tn, data) in expired.items():
            package = self.get_package(tn)
            self._raw_message(None,
                '{d[owner]}: {p.carrier} hasn\'t found your "{d[tag]}" yet so I\'m dropping it'.format(
                    d=data, p=package))
            del self._unready_data[tn]

        delivered = []
        for (tn, data) in self._data.items():
            package = self.get_package(tn)
            try:
                new_state = package.track()
            except TrackingFailure as e:
                self.log_warning(e)
                continue
            new_update = int(time.mktime(new_state.last_update.timetuple()))
            if new_state.is_delivered:
                delivered.append(tn)
            if data['last_update'] < new_update:
                self._data[tn]['last_update'] = new_update
                self.save_data()
                self.output_status(package)
            yield
        for tn in delivered:
            del self._data[tn]
        self.save_data()

    def output_status(self, package):
        try:
            state = package.track()
            data = self._data[package.tracking_number]
        except Exception:
            traceback.print_exc()
            return
        if state.is_delivered:
            msg = '{package.carrier} has delivered "{data[tag]}"'.format(
                package=package, data=data)
        elif len(state.events) > 1:
            msg = '{package.carrier} moved "{data[tag]}" from {oldstate.detail}@{oldstate.location} to {newstate.status}@{newstate.location}'.format(
                data=data,
                package=package,
                oldstate=state.events[-2],
                newstate=state)
        else:
            msg = '{package.carrier} moved "{data[tag]}" to {newstate.status}@{newstate.location}'.format(
                data=data,
                package=package,
                newstate=state)
        if not state.is_delivered and state.delivery_date:
            hours = int((state.delivery_date - datetime.datetime.now()).total_seconds() // 3600)
            msg += ', delivery is T minus {hours} hours'.format(hours=hours)
        msg = '{owner}: {msg} <{url}>'.format(
            url=short_url(package.url),
            owner=data['owner'],
            msg=msg)
        if data['direct'] and False:
            for plgn in self.parent._plugins:
                if isinstance(plgn, IRCPlugin):
                    plgn.bot.connection.privmsg(data['owner'], msg)
                    break
        else:
            self._raw_message(data['channels'], msg)

    def _raw_message(self, chans, msg):
        self.parent.send_outgoing('default', msg)
        #for chan in chans:
        #    self.parent.send_outgoing(chan, msg)

    @property
    def poll_interval(self):
        base_interval = 300
        return base_interval if len(self._data) < 2 else (base_interval / len(self._data))

    def save_data(self):
        with open(self._persist_file, 'wb') as pf:
            json.dump(self._data, pf, indent=4)

    def load_data(self):
        try:
            with open(self._persist_file, 'rb') as pf:
                self._data.update(json.load(pf))
        except (IOError, ValueError):
            pass

    def get_package(self, tn):
        return packagetrack.Package(tn)

    def _generate_tag(self, tn):
        if self._word_database is not None:
            return ' '.join(random.choice(self._word_database).capitalize() for i in range(3))
        else:
            return tn


class PackageStatus(CommandPlugin):
    def __init__(self, core, auth_file=None):
        super(PackageStatus, self).__init__(core)
        packagetrack.auto_register_carriers(DotFileConfig(auth_file))

    @CommandPlugin.register_command(r"pstatus(?:\s+([\w\d]+))?")
    def status_command(self, chans, name, match, direct, reply):
        if not match.group(1):
            reply('What exactly do you want the status of?')
            return
        tn = match.group(1)
        package = self.get_package(tn)
        try:
            info = package.track()
        except UnsupportedTrackingNumber:
            self.log_warning('UnsupportedShipper: {0}'.format(tn))
            reply('Dunno any carriers for a number like that')
        except TrackingFailure as err:
            reply('Sorry, {p.carrier} said "{msg}" <{url}>'.format(
                p=package, msg=err, url=short_url(package.url)))
        except Exception as e:
            msg = '({tn}) {etype}: {message}'.format(
                etype=e.__class__.__name__, message=e.message, tn=tn)
            self.log_warning(msg)
            reply(msg)
        else:
            if info.is_delivered:
                msg = '{p.carrier} says it has been delivered as of {last_update}'
            else:
                msg = '{p.carrier} has it at {i.status}@{i.location} as of {last_update}, ' + \
                    'and it should be delivered {delivery_date}'
            msg += ' <{url}>'
            delivery_date = '... eventually' if info.delivery_date is None else \
                ('today' if info.delivery_date.date() == datetime.date.today() else info.delivery_date.strftime('%m/%d'))
            reply(msg.format(
                p=package,
                i=info,
                last_update=info.last_update.strftime('%m/%d %H:%M'),
                delivery_date=delivery_date,
                url=short_url(package.url)))

    def get_package(self, tn):
        return packagetrack.Package(tn)
