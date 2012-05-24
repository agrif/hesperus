import packagetrack
import time
import datetime
from ..plugin import PollPlugin, CommandPlugin
from ..shorturl import short_url

class FollowingPlugin(CommandPlugin, PollPlugin):
    poll_interval = 120

    @CommandPlugin.config_types(persist_file=str)
    def __init__(self, core, persist_file='shipping-following.json'):
        super(FollowingPlugin, self).__init__(core)
        self._persist_file = persist_file
        self._data = {}
        self.load_data()
        
    @CommandPlugin.register_command(r"ptrack(?:\s+([\w\d]+))?")
    def track_command(self, chans, name, match, direct, reply):
        if match.group(1):
            tn = match.group(1)
            if tn in self._data.keys():
                del self._data[tn]
                self.save_data()
                reply('WELL FINE THEN, I won\'t tell you about that package anymore')
            else:
                package = packagetrack.Package(tn)
                try:
                    state = package.track()
                except (packagetrack.UnsupportedShipper,
                        packagetrack.service.InvalidTrackingNumber):
                    self.log_warning('bad tracking number: {}'.format(tn))
                    reply('I don\'t know how to deal with that number')
                else:
                    self._data[tn] = int(time.mktime(state.last_update.timetuple()))
                    self.save_data()
                    reply('Looks like that package is at {state} right now, I\'ll let you know when it changes'.format(state=state.status))
        else:
            packages = map(packagetrack.Package, self._data.keys())
            if packages:
                reply('I\'m watching these packages: {}'.format(
                    ', '.join('({shipper}){tn}'.format(
                        shipper=p.shipper, tn=p.tracking_number) for p in packages)))
            else:
                reply('I\'m not watching any packages right now')

    def poll(self):
        for (tn, last_check) in self._data.items():
            package = packagetrack.Package(tn)
            new_state = package.track()
            new_update = int(time.mktime(new_state.last_update.timetuple()))
            if last_check < new_update:
                self._data[tn] = new_update
                self.output_status(package)
            yield

    def output_status(self, package):
        for chan in self._channels:
            self.parent.send_outgoing(chan,
                '{shipper} moved {tn} to {state} ({url})'.format(
                    tn=package.tracking_number,
                    shipper=package.shipper,
                    state=package.track().status,
                    url=short_url(package.url())))

    def save_data(self):
        with open(self._persist_file, 'wb') as pf:
            json.dump(self._data, pf, indent=4)

    def load_data(self):
        try:
            with open(self._persist_file, 'rb') as pf:
                self._data.update(json.load(pf))
        except (IOError, ValueError):
            pass


class TrackingPlugin(CommandPlugin):
    def __init__(self, core, auth_file=None):
        super(TrackingPlugin, self).__init__(core)
        self.auth_file = auth_file

    @CommandPlugin.register_command(r"pstatus\s+([\w\d]+)")
    def status_command(self, chans, name, match, direct, reply):
        tn = match.group(1)
        package = packagetrack.Package(tn, configfile=self.auth_file)
        try:
            info = package.track()
        except packagetrack.UnsupportedShipper:
            self.log_warning('UnsupportedShipper: {}'.format(tn))
            reply('Dunno any shippers for a number like that')
        except packagetrack.service.InvalidTrackingNumber:
            self.log_warning('InvalidTrackingNumber: {}'.format(tn))
            reply('Are you sure you that\'s the right number?')
        except Exception as e:
            msg = '({tn}) {etype}: {message}'.format(
                etype=e.__class__.__name__, message=e.message, tn=tn)
            self.log_warning(msg)
            reply(msg)
        else:
            msg = '{carrier} has it at {status} as of {last_update}, '+ \
                'should be delivered on {delivery_date} ({url})'
            reply(msg.format(
                carrier=package.shipper,
                status=info.status,
                last_update=info.last_update.strftime('%m/%d %H:%M'),
                delivery_date=info.delivery_date.strftime('%m/%d') \
                    if info.delivery_date is not None else 'UNKNOWN',
                url=short_url(package.url())))
