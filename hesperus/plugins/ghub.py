import time
import urllib2
import json
import re
from datetime import datetime
from time import time, sleep
from copy import copy
from posixpath import split as posix_split

from github.github import GitHub

from ..plugin import PollPlugin, CommandPlugin
from ..core import ET, ConfigurationError
from ..shorturl import short_url as _short_url

# how each event is printed
DEFAULT_FORMATS = {
    'PushEvent' : "{actor} pushed {payload[size]} commit{payload[plural]} to {payload[ref]} at {repository[owner]}/{repository[name]} ({url})",
    'IssuesEvent' : "{actor} {payload[action]} issue #{payload[number]}: \"{payload[issue][title]}\" on {repository[owner]}/{repository[name]} ({url})",
    'IssueCommentEvent' : "{actor} commented on issue #{payload[number]}: \"{payload[issue][title]}\" on {repository[owner]}/{repository[name]}: \"{payload[body_short]}\" ({url})",
    'CommitCommentEvent' : "{actor} commented on commit {payload[commit]} on {repository[owner]}/{repository[name]} ({url})",
    'GollumEvent' : "{actor} {payload[pages][0][action]} \"{payload[pages][0][title]}\" in the {repository[owner]}/{repository[name]} wiki ({url})",
    'CreateEvent' : "{actor} created {payload[ref_type]} {payload[ref]} at {repository[owner]}/{repository[name]} ({url})",
    'DeleteEvent' : "{actor} deleted {payload[ref_type]} {payload[ref]} at {repository[owner]}/{repository[name]} ({url})",
    'PullRequestEvent' : "{actor} {payload[action]} pull request {payload[number]}: \"{payload[pull_request][title]}\" on {repository[owner]}/{repository[name]} ({url})",
    'WatchEvent' : "{actor} {payload[action]} watching {repository[owner]}/{repository[name]} ({url})",
    'DownloadEvent' : "{actor} uploaded \"{payload[filename]}\" to {repository[owner]}/{repository[name]} ({url})",
    'MemberEvent' : "{actor} {payload[action]} {payload[member]} to {repository[owner]}/{repository[name]} ({url})",
}

# pretty string trunc function
# <http://kelvinwong.ca/2007/06/22/a-nicer-python-string-truncation-function/>
# from Kelvin Wong, under the license at http://www.python.org/psf/license/
def _trunc(s, min_pos=0, max_pos=75, ellipsis=True):
    # Sentinel value -1 returned by String function rfind
    NOT_FOUND = -1
    # Error message for max smaller than min positional error
    ERR_MAXMIN = 'Minimum position cannot be greater than maximum position'
    
    # If the minimum position value is greater than max, throw an exception
    if max_pos < min_pos:
        raise ValueError(ERR_MAXMIN)
    # Change the ellipsis characters here if you want a true ellipsis
    if ellipsis:
        suffix = '...'
    else:
        suffix = ''
    # Case 1: Return string if it is shorter (or equal to) than the limit
    length = len(s)
    if length <= max_pos:
        return s + suffix
    else:
        # Case 2: Return it to nearest period if possible
        try:
            end = s.rindex('.',min_pos,max_pos)
        except ValueError:
            # Case 3: Return string to nearest space
            end = s.rfind(' ',min_pos,max_pos)
            if end == NOT_FOUND:
                end = max_pos
        return s[0:end] + suffix

# make refs look nice
def _nice_ref(ref):
    if ref.startswith('refs/heads/'):
        return ref.split('/', 2)[2]
    return ref

# automatically spaces out github requests!
class AutoDelayGitHub:
    def __init__(self, delay=1.0):
        self.gh = GitHub()
        self.lasttime = 0
        self.delay = delay

    def __getattr__(self, name):
        while time() < self.lasttime + self.delay:
            sleep(self.lasttime + self.delay - time())
        self.lasttime = time()
        return getattr(self.gh, name)

class GitHubPlugin(CommandPlugin, PollPlugin):
    poll_interval = 50
    commands_queued = False
    
    @PollPlugin.config_types(feedmap=ET.Element, issues_default_user=str, issues_default_repo=str)
    def __init__(self, core, feedmap=None, default_user="agrif", default_repo="hesperus"):
        super(GitHubPlugin, self).__init__(core)
        
        self.default_user = default_user
        self.default_repo = default_repo
        self.feedmap = {}
        self.events_cached = {}

        if feedmap == None:
            feedmap = []
        for el in feedmap:
            if not el.tag.lower() == 'feed':
                raise ConfigurationError('feedmap must contain feed tags')
            channel = el.get('channel', None)
            feed_url = el.text
            if not channel or not feed_url:
                raise ConfigurationError('invalid feed tag')
            
            if not feed_url in self.feedmap:
                self.feedmap[feed_url] = [channel]
                self.events_cached[feed_url] = []
            else:
                self.feedmap[feed_url].append(channel)
        
        self.gh = AutoDelayGitHub()
        
    def get_events(self, url):
        #self.log_debug("fetching", url)
        r = urllib2.Request(url)
        retdata = urllib2.urlopen(r).read()
            
        retdata = json.loads(retdata)
        # ex. "2011/03/22 00:49:44 -0700"
        timefmt = "%Y/%m/%d %H:%M:%S" # timezone is ignored, split off
        for event in retdata:
            event['created_at'] = event['created_at'].rsplit(' ', 1)[0]
            event['created_at'] = datetime.strptime(event['created_at'], timefmt)
        return retdata
        
    def postprocess_event(self, e):
        event = copy(e)
        if 'payload' in event:
            payload = event['payload']
            if 'ref' in payload:
                payload['ref'] = _nice_ref(payload['ref'])
            if 'size' in payload:
                payload['plural'] = ''
                if payload['size'] != 1:
                    payload['plural'] = 's'
                if 'commit' in payload:
                    payload['commit'] = payload['commit'][:6]
        if event['type'] == 'IssuesEvent':
            payload = event['payload']
            issue = self.gh.issues.show(event['repository']['owner'], event['repository']['name'], payload['number'])
            payload['issue'] = issue.__dict__
        if event['type'] == 'IssueCommentEvent':
            payload = event['payload']
            try:
                payload['number'] = int(event['url'].split('/issues/', 1)[1].split("#", 1)[0])
                
                issue = self.gh.issues.show(event['repository']['owner'], event['repository']['name'], payload['number'])
                payload['issue'] = issue.__dict__
                
                comments = self.gh.issues.comments(event['repository']['owner'], event['repository']['name'], payload['number'])
                comments = filter(lambda c: c.id == payload['comment_id'], comments)
                if comments:
                    body = comments[0].body
                    payload['body'] = body
                    body_short = re.sub(r'\s+', ' ', body)
                    body_short = _trunc(body_short)
                    payload['body_short'] = body_short
                else:
                    payload['body'] = ''
                    payload['body_short'] = ''
                
            except (TypeError, ValueError):
                pass
        if event['type'] == 'DownloadEvent':
            payload = event['payload']
            payload['filename'] = posix_split(payload['url'])[1]
            event['url'] = payload['url']
        if 'url' in event:
            event['url'] = _short_url(event['url'])
        return event
    
    def start(self):
        # fetch the initial cache of events
        for url in self.feedmap:
            self.events_cached[url] = self.get_events(url)
        
        super(GitHubPlugin, self).start()
    
    def poll(self):
        for feed in self.feedmap:
            try:
                events_new = self.get_events(feed)
            except (urllib2.HTTPError, urllib2.URLError):
                # try again later
                self.log_warning("fetch failed:", feed)
                return
            yield
            
            channels = self.feedmap[feed]
            old = self.events_cached[feed]
            if len(old) > 0:
                last_update = old[0]['created_at']
                yield
                new = filter(lambda x: x['created_at'] > last_update, events_new)
            else:
                new = events_new
            yield
            
            for e in new:
                event = self.postprocess_event(e)
                yield
                
                if not event['type'] in DEFAULT_FORMATS:
                    self.log_warning("unhandled event", event['type'])
                else:
                    msg = DEFAULT_FORMATS[event['type']]
                    try:
                        msg = msg.format(**event)
                        self.log_message(msg)
                        for chan in self.feedmap[feed]:
                            self.parent.send_outgoing(chan, msg)
                    except Exception, ex:
                        self.log_warning("error while formatting event", repr(event))
                
                yield
            
            self.events_cached[feed] = events_new
    
    @CommandPlugin.register_command(r"(?:issue|pull)s?(?:\s+help)?")
    def issue_help_command(self, chans, name, match, direct, reply):
        reply("Usage: issue <number or search string> [in name/repo]")
        
    @CommandPlugin.register_command(r"(?:issue|pull)s?\s+(?:(?:#?([0-9]+))|(.+?))(?:\s+(?:in|for|of|on)\s+([a-zA-Z0-9._-]+))?")
    def issue_command(self, chans, name, match, direct, reply):
        #reply("match: %s" % (repr(match.groups()),))
        user = match.group(3)
        if user is None:
            user = self.default_user
        repo = self.default_repo
        
        issues = []
        try:
            if match.group(1) is None:
                search = match.group(2)
                issues = self.gh.issues.search(user, repo, "open", search)
            else:
                issue_id = int(match.group(1))
                issues = [self.gh.issues.show(user, repo, issue_id)]
        except urllib2.HTTPError:
            issues = []
        
        issues = issues[:3]
        for i in issues:
            i.html_url = _short_url(i.html_url)
            reply("Issue #{number}: \"{title}\" ({state}) {html_url}".format(**i.__dict__))
        if len(issues) == 0:
            reply("no issues found :(")
    
    @CommandPlugin.register_command(r"([^\:]+)\:([0-9]+)(?:\s+(?:in|for|of|on)\s+([a-zA-Z0-9._-]+)(?:/([a-zA-Z0-9._-]+))?)?")
    def file_line_command(self, chans, name, match, direct, reply):
        fname = match.group(1)
        lineno = match.group(2)
        user = match.group(3)
        if user is None:
            user = self.default_user
        repo = self.default_repo
        branch = match.group(4)
        if branch is None:
            branch = "master"
        
        url_format = "https://github.com/{user}/{repo}/blob/{branch}/{fname}#L{lineno}"
        reply(_short_url(url_format.format(
                    user=user, repo=repo, branch=branch, fname=fname, lineno=lineno)))
