import packagetrack
import time

from ..plugin import PollPlugin, CommandPlugin
from ..shorturl import short_url

class FollowingPlugin(PollPlugin, CommandPlugin):
    pass

class TrackingPlugin(CommandPlugin):
    @CommandPlugin.register_command(r'track\s+([\w\d]+)')
    def track_command(self, chans, name, match, direct, reply):
        tn = match.group(1)
        package = packagetrack.Package(tn)
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
                delivery_date=info.delivery_date.strftime('%m/%d'),
                url=short_url(package.url())))
