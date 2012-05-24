import packagetrack
import time

from ..plugin import PollPlugin, CommandPlugin

class FollowingPlugin(PollPlugin, CommandPlugin):
    pass

class TrackingPlugin(CommandPlugin):
    @CommandPlugin.register_command(r'track\s+([\w\d]+)')
    def track_command(self, chans, name, match, direct, reply):
        tn = match.group(1)
        package = packagetrack.Package(match.group(1))
        try:
            info = package.track()
        except Exception as e:
            reply('OH NO: {error}'.format(error=e.message))
        else:
            msg = '{carrier} has your stuff at {status} as of {last_update}, '+ \
                'you can expect it dumped on your doorstep on {delivery_date}'
            reply(msg.format(
                carrier=package.shipper,
                status=info.status,
                last_update=info.last_update.strftime('%m/%d %H:%M'),
                delivery_date=info.delivery_date.strftime('%m/%d'))
