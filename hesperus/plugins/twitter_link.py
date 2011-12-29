from ..plugin import PassivePlugin
import twitter
import htmllib

def html_entity_unescape(s):
    p = htmllib.HTMLParser(None)
    p.save_bgn()
    p.feed(s)
    return p.save_end()

class TwitterLinkPlugin(PassivePlugin):
    @PassivePlugin.config_types(api_id=str)
    def __init__(self, core, api_id=''):
        super(TwitterLinkPlugin, self).__init__(core)
        #TODO actually use the api_id to allow authenticated api requests
        self.twitter_api = twitter.Api()
    
    @PassivePlugin.register_pattern(r"\bhttps?://(?:(?:www\.)?twitter.com/\#\!|mobile.twitter.com)/(?P<user>\w+)/status/(?P<sid>\d+)\b")
    def status_message_pattern(self, match, reply):
        sid = int(match.groupdict()['sid'])
        user = match.groupdict()['user']
        try:
            status = html_entity_unescape(self.twitter_api.GetStatus(sid).text)
        except twitter.TwitterError, error:
            self.log_warning('Twitter error:', error.message)
        else:
            reply('%s tweeted: %s' % (user, status))
