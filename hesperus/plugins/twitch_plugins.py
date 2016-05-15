from ..plugin import CommandPlugin, PollPlugin, PersistentPlugin
from ..shorturl import short_url

from twitch.api import v3 as twitch_api_v3
from twitch.exceptions import ResourceUnavailableException

class TwitchWatcherPlugin(PollPlugin, CommandPlugin, PersistentPlugin):
	MSG_STARTED_STREAM	= '{owner} started streaming "{game}": <{url}>'
	MSG_STOPPED_STREAM	= '{owner} has stopped streaming "{game}"'

	persistence_file	= 'twitch_watcher.json'
	_data 				= {
		'watched':	{},
	}

	def display_usage(self, reply):
		pass

	@PollPlugin.config_types(poll_interval=int)
	def __init__(self, core, poll_interval=300, *args):
		super(TwitchWatcherPlugin, self).__init__(core, *args)
		self._base_interval = poll_interval

		self.load_data()

	@CommandPlugin.register_command(r'watchme(?:\s+(?P<username>[\w\d_]+))?')
	def watch_cmd(self, chans, name, match, direct, reply):
		twitch_username = match.groupdict()['username']
		if twitch_username is None:
			return self.display_usage(reply)

		if twitch_username in self._data['watched']:
			if self._data['watched'][twitch_username]['owner'] == name:
				del self._data['watched'][twitch_username]
				reply('Ok, I\'m not watching your channel anymore')
				return self.save_data()
			else:
				return reply('You can\'t tell me what to do!')

		try:
			twitch_channel = self._get_channel(twitch_username)
		except ResourceUnavailableException:
			return reply('Couldn\'t find a channel by that name')

		self._data['watched'][twitch_username] = {
			'owner':	name,
			'game':		None,
			'live':		False,
		}
		reply('Ok, I\'ll watch your shitty channel')
		return self.save_data()

	@property
	def poll_interval(self):
		return self._base_interval if len(self._data['watched']) < 2 else \
			(self._base_interval / len(self._data['watched']))

	def poll(self):
		require_save = False
		for twitch_username, data in self._data['watched'].iteritems():
			stream = self._get_stream(twitch_username)
			if bool(stream) == data['live']:
				# no change in live status
				pass
			else:
				if bool(stream):
					# started streaming
					self._data['watched'][twitch_username]['game'] = stream['game']
					self._data['watched'][twitch_username]['live'] = True
					require_save = True

					self._raw_message(self.MSG_STARTED_STREAM.format(
						owner=data['owner'], game=stream['game'], url=stream['channel']['url']))
				else:
					# stopped streaming
					self._raw_message(self.MSG_STOPPED_STREAM.format(
						owner=data['owner'], game=data['game']))

					self._data['watched'][twitch_username]['game'] = None
					self._data['watched'][twitch_username]['live'] = False
					require_save = True

			if require_save:
				self.save_data()
			yield


	def _get_channel(self, channel_name):
		return twitch_api_v3.channels.by_name(channel_name)

	def _get_stream(self, channel_name):
		resp = twitch_api_v3.streams.by_channel(channel_name)
		return resp['stream']

	def _raw_message(self, message):
		self.parent.send_outgoing('default', message)