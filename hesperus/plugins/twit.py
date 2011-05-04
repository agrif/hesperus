from ..plugin import PollPlugin
from ..core import ET, ConfigurationError
from ..shorturl import short_url
import time
import twitter

class TwitterPlugin(PollPlugin):
    poll_interval = 50
    
    @PollPlugin.config_types(usernames=ET.Element)
    def __init__(self, core, usernames=None):
        super(TwitterPlugin, self).__init__(core)
        
        self.usernames = []
        self.last_update = time.time()

        if usernames == None:
            usernames = []
        for el in usernames:
            if not el.tag.lower() == 'username':
                raise ConfigurationError('usernames must contain username tags')
            self.usernames.append(el.text)
        
        self.twitter = twitter.Api()
        
    def poll(self):
        new_tweets = []
        for username in self.usernames:
            statuses = self.twitter.GetUserTimeline(username)
            yield
            statuses = filter(lambda s: s.created_at_in_seconds > self.last_update, statuses)
            statuses = filter(lambda s: not s.text.startswith("@"), statuses)
            yield
            new_tweets += statuses
        yield
        
        new_tweets = sorted(new_tweets, key=lambda s: s.created_at_in_seconds)
        yield
        
        self.last_update = max(map(lambda s: s.created_at_in_seconds, new_tweets))
        
        for tweet in new_tweets:
            msg = "@{s.user.screen_name} tweeted: {s.text}"
            msg = msg.format(s=tweet)
            for chan in self.channels:
                self.parent.send_outgoing(chan, msg)
            self.log_message(msg)
            yield
