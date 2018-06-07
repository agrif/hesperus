import hashlib

from ..plugin import CommandPlugin, PollPlugin, PersistentPlugin
from ..shorturl import short_url

from twitch.api import v3 as twitch_api_v3
from twitch.exceptions import ResourceUnavailableException

class TwitchWatcherPlugin(PollPlugin, CommandPlugin, PersistentPlugin):
	MSG_STARTED_STREAM		= '{owner} started streaming "{game}": <{url}>'
	MSG_STOPPED_STREAM		= '{owner} has stopped streaming "{game}"'
	MSG_CHANGED_STREAM		= '{owner} has changed games to "{game}"'
	MSG_STREAM_STATUS		= '{owner} ({status}): <{url}>'
	MSG_WATCHME_USAGE		= '!watchme <twitch channel>'
	MSG_NO_CHANNELS_KNOWN	= 'I\'m not watching any twitch channels'
	MSG_STOPPED_WATCHING	= 'Fine, I won\'t watch your channel anymore. You ' \
								'suck at games anyway'
	MSG_NO_CHANNEL_FOUND	= 'There\'s no channel with that name, lrn2type scrub'
	MSG_STARTED_WATCHING	= 'Ok, I\'ll watch your shitty channel'
	MSG_CHALLENGE_RESP		= 'Prove that is really your channel by putting ' \
								'"{key}" in your channel status then try again ' \
								'after a minute or two'

	persistence_file	= 'twitch_watcher.json'
	_data 				= {
		'watched':	{},
	}

	@PollPlugin.config_types(poll_interval=int, msg_on_game_change=bool)
	def __init__(self, core, poll_interval=90, msg_on_game_change=False, *args):
		super(TwitchWatcherPlugin, self).__init__(core, *args)
		self._base_interval = poll_interval
		self._msg_on_game_change = msg_on_game_change

		self.load_data()

	@CommandPlugin.register_command(r'twitch')
	def status_cmd(self, chans, name, match, direct, reply):
		if len(self._data['watched']) > 0:
			for irc_username, data in self._data['watched'].iteritems():
				status = 'live' if data['live'] else 'offline'
				reply(self.MSG_STREAM_STATUS.format(
					owner=irc_username, status=status, url=data['url']))
		else:
			reply(self.MSG_NO_CHANNELS_KNOWN)

	@CommandPlugin.register_command(r'watchme(?:\s+(?P<username>[\w\d_]+))?')
	def watch_cmd(self, chans, name, match, direct, reply):
		twitch_username = match.groupdict()['username']
		if twitch_username is None:
			return reply(self.MSG_WATCHME_USAGE)

		if name in self._data['watched']:
			del self._data['watched'][name]
			reply(self.MSG_STOPPED_WATCHING)
			return self.save_data()

		try:
			twitch_channel = self._get_channel(twitch_username)
		except ResourceUnavailableException:
			return reply(self.MSG_NO_CHANNEL_FOUND)

		auth_key = self._build_auth_key(name, twitch_username)
		if auth_key in twitch_channel['status']:
			self._data['watched'][name] = {
				'twitch_username':	twitch_username,
				'game':				None,
				'live':				False,
				'url':				twitch_channel['url'],
			}
			reply(self.MSG_STARTED_WATCHING)
			return self.save_data()
		else:
			self.log_debug('Found channel status as: {}'.format(twitch_channel['status']))
			return reply(self.MSG_CHALLENGE_RESP.format(key=auth_key))

	@property
	def poll_interval(self):
		return self._base_interval if len(self._data['watched']) < 2 else \
			(self._base_interval / len(self._data['watched']))

	def poll(self):
		require_save = False
		for irc_username, data in self._data['watched'].iteritems():
			stream = self._get_stream(data['twitch_username'])
			stream_is_live = bool(stream) and stream['average_fps'] > 5

			if stream_is_live == data['live']:
				# no change in live status
				if self._msg_on_game_change and \
						stream_is_live and \
						stream['game'] != data['game']:
					# changed games
					self._raw_message(self.MSG_CHANGED_STREAM.format(
						owner=irc_username, game=stream['game']))

					self._data['watched'][irc_username]['game'] = stream['game']
					require_save = True
			else:
				if stream_is_live and stream['average_fps'] > 5:
					# started streaming
					self._data['watched'][irc_username]['game'] = stream['game']
					self._data['watched'][irc_username]['live'] = True
					require_save = True

					self._raw_message(self.MSG_STARTED_STREAM.format(
						owner=irc_username, game=stream['game'].encode('ascii', errors='ignore'), url=stream['channel']['url']))
				else:
					# stopped streaming
					#self._raw_message(self.MSG_STOPPED_STREAM.format(
					#	owner=irc_username, game=data['game']))

					self._data['watched'][irc_username]['game'] = None
					self._data['watched'][irc_username]['live'] = False
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

	def _build_auth_key(self, irc_username, twitch_username):
		h = hashlib.sha1('{}:{}'.format(irc_username, twitch_username)).hexdigest()
		return 'watchme-{}'.format(h[:16])
