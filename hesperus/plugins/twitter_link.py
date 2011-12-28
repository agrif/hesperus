from ..plugin import PassivePlugin
import twitter

class TwitterLinkPlugin(PassivePlugin):
    @PassivePlugin.config_types(api_id=str)
    def __init__(self, core, api_id=''):
        super(TwitterLinkPlugin, self).__init__(core)
        self.twitter_api = twitter.Api()
    
    @PassivePlugin.register_pattern("\bhttps?://(?:www\.)?twitter.com/\#\!/(?P<user>\w+)/status/(?P<sid>\d+)\b")
    def status_message_pattern(self, match, reply):
        sid = int(match.groupdict()['sid'])
        status = self.twitter_api.GetStatus(sid)
        reply('%s tweeted: %s' % status.user.screen_name, status.text)