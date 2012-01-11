import time
import urllib2
from urllib import urlencode
import json
import re
from datetime import datetime
from time import time, sleep
from copy import copy
from posixpath import split as posix_split

from github.github import GitHub

from ..plugin import PollPlugin, CommandPlugin
from ..core import ET, ConfigurationError
from ..shorturl import short_url
_short_url = lambda u: short_url(u, provider="git.io")

# how each event is printed
DEFAULT_FORMATS = {
    'PushEvent' : "{actor} pushed {payload[size]} commit{payload[plural]} to {payload[ref]} at {repository[owner]}/{repository[name]} {url}",
    'IssuesEvent' : "{actor} {payload[action]} issue #{payload[number]}: \"{payload[issue][title]}\" on {repository[owner]}/{repository[name]} {url}",
    'IssueCommentEvent' : "{actor} commented on issue #{payload[number]}: \"{payload[issue][title]}\" on {repository[owner]}/{repository[name]}: \"{payload[body_short]}\" {url}",
    'CommitCommentEvent' : "{actor} commented on commit {payload[commit]} on {repository[owner]}/{repository[name]} {url}",
    'GollumEvent' : "{actor} {payload[pages][0][action]} \"{payload[pages][0][title]}\" in the {repository[owner]}/{repository[name]} wiki {url}",
    'CreateEvent' : "{actor} created {payload[ref_type]} {payload[ref]} at {repository[owner]}/{repository[name]} {url}",
    'DeleteEvent' : "{actor} deleted {payload[ref_type]} {payload[ref]} at {repository[owner]}/{repository[name]} {url}",
    'PullRequestEvent' : "{actor} {payload[action]} pull request {payload[number]}: \"{payload[pull_request][title]}\" on {repository[owner]}/{repository[name]} {url}",
    'WatchEvent' : "{actor} {payload[action]} watching {repository[owner]}/{repository[name]} {url}",
    'DownloadEvent' : "{actor} uploaded \"{payload[filename]}\" to {repository[owner]}/{repository[name]} {url}",
    'MemberEvent' : "{actor} {payload[action]} {payload[member]} to {repository[owner]}/{repository[name]} {url}",
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

class MiniGithubAPI(object):
    """For version 3 of the API, since the py-github libraries use the older
    version and try to parse github's xml that is occasionally malformed.

    This lib is dead simple: you pass in the URL and a dict of query args, and
    this returns the JSON. GET requests only, no authentication, just data
    retrieval.

    See http://developer.github.com/v3/
    """
    def __init__(self, baseurl=None, delay=1.0):
        if not baseurl:
            self.baseurl = "https://api.github.com"
        else:
            self.baseurl = baseurl
        self.delay = delay
        self.lasttime = 0

    def query(self, url, args=None, raw=False):
        """Give a url such as:
            /repos/someuser/somerepo/branches

        args is a dictionary with any additional query parameters to pass, such
        as pagination options

        raw mode will set the accept header to application/vnd.github.raw,
        which will not return a json decoded object but rather the raw string
        data that github sends.
        """
        if url.startswith(self.baseurl):
            pass
        elif not url.startswith("/"):
            raise ValueError("That doesn't look like a URL path")
        else:
            url = self.baseurl + url

        while time() < self.lasttime + self.delay:
            sleep(self.lasttime + self.delay - time())
        self.lasttime = time()

        if args:
            argstring = "?" + urlencode(args)
        else:
            argstring = ""

        completeurl = url + argstring
        reqobj = urllib2.Request(completeurl)
        if raw:
            reqobj.add_header("Accept", "application/vnd.github.raw")
        request = urllib2.urlopen(reqobj)

        if raw:
            return request.read()
        return json.load(request)

class GitHubPlugin(CommandPlugin, PollPlugin):
    poll_interval = 50
    # Run command callbacks (register_command decorated methods) in the main
    # thread, not in the plugin's thread
    commands_queued = False
    
    @PollPlugin.config_types(feedmap=ET.Element, default_user=str, default_repo=str)
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
        self.gh3 = MiniGithubAPI()

        self.firstrun = True
        
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
    
    def poll(self):
        if self.firstrun:
            # fetch the initial cache of events
            for url in self.feedmap:
                self.events_cached[url] = self.get_events(url)
            self.firstrun = False

        for feed in self.feedmap:
            try:
                events_new = self.get_events(feed)
                yield
            except (urllib2.HTTPError, urllib2.URLError):
                # try again later
                self.log_warning("fetch failed:", feed)
                yield
                continue
            
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
    
    @CommandPlugin.register_command(r"(issue|pull|patch|diff)s?(?:\s+help)?")
    def issue_help_command(self, chans, name, match, direct, reply):
        cmd = match.group(1)
        reply("Usage: %s <number or search string> [in name/repo]" % (cmd,))
        
    @CommandPlugin.register_command(r"(issue|pull|patch|diff)s?\s+(?:(?:#?([0-9]+))|(.+?))(?:\s+(?:in|for|of|on)\s+([a-zA-Z0-9._-]+))?")
    def issue_command(self, chans, name, match, direct, reply):
        #reply("match: %s" % (repr(match.groups()),))
        cmd = match.group(1)
        user = match.group(4)
        if user is None:
            user = self.default_user
        repo = self.default_repo
        
        issues = []
        try:
            if match.group(2) is None:
                search = match.group(3)
                issues = self.gh.issues.search(user, repo, "open", search)
            else:
                issue_id = int(match.group(2))
                issues = [self.gh.issues.show(user, repo, issue_id)]
        except urllib2.HTTPError:
            issues = []
        
        issues.reverse()
        issues = issues[:3]
        for i in issues:
            if cmd in ('pull', 'patch', 'diff'):
                if not 'pull_request_url' in i.__dict__:
                    continue
                i.html_url = i.pull_request_url
            if cmd == 'patch':
                i.html_url += '.patch'
            elif cmd == 'diff':
                i.html_url += '.diff'
            
            i.html_url = _short_url(i.html_url)
            reply(cmd.capitalize() + " #{number}: \"{title}\" ({state}) {html_url}".format(**i.__dict__))
        if len(issues) == 0:
            reply("no issues found :(")
    
    @CommandPlugin.register_command(r"([^:]+):([0-9]+)(?:\s+(?:in|for|of|on)\s+([a-zA-Z0-9._-]+)(?:/([a-zA-Z0-9._-]+))?)?")
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
        
        # Get the tree for the specified branch or commit
        try:
            tree = self.gh3.query("/repos/{user}/{repo}/git/trees/{branch}".format(
                user=user,repo=repo,branch=branch),
                    dict(recursive=1))
        except urllib2.HTTPError:
            reply("I couldn't find that user or branch. Sorry!")
            return

        # Look through it to find the file we're looking for
        for fileinfo in tree['tree']:
            if fileinfo['path'] == fname:
                break
            # Also match the filename even if the path wasn't correct
            if fileinfo['path'].endswith(fname):
                break
        else:
            reply("Sorry, I couldn't locate that file in %s/%s" % (user,branch))
            return

        if fileinfo['type'] == "tree":
            reply("That's not a file, that's a directory!")
            return

        # Blob requests for empty files returns 404 from the github api
        # apparently
        if fileinfo['size'] == 0:
            reply("That file appears to be empty.")
            return

        # At this point, we have the file's info in fileinfo
        # Correct for the path if just a filename was given but we found it in
        # a sub-folder
        fname = fileinfo['path'].encode("UTF-8")


        # Download that file
        file_contents = self.gh3.query(fileinfo['url'], raw=True)

        # Do a quick check to see if it's a binary file
        if "\0" in file_contents:
            reply("Hey! Just what do you think you're trying to pull?")
            return

        file_lines = file_contents.split("\n")

        lineno = int(lineno)
        if lineno == 0:
            reply("There is no line zero")
            return

        if len(file_lines) < lineno:
            reply("That file doesn't have that many lines! It only has %s" % len(file_lines))
            return

        reply("File %s line %s:" % (fname, lineno))

        # Reply with the line itself
        line = file_lines[lineno-1].rstrip()
        if len(line) > 80:
            line = line[:77] + "..."
        # Don't print a blank line
        if line.strip():
            reply(line.lstrip())

        # Search backwards for the first function definition line
        wslen = lambda s: len(re.match(r"\s*", s).group())
        whitespace = wslen(line)

        funcmatch = re.compile(r"(\s*)def (\w+)\(")
        methmatch = re.compile(r"(\s*)def (\w+)\(self")
        classmatch = re.compile(r"(\s*)class (\w+)\(")

        if lineno > 1:
            for otherline in reversed(file_lines[:lineno-1]):
                # Ignore blank lines
                if not otherline.strip():
                    continue
                
                # Check this line
                mmatched = methmatch.match(otherline)
                fmatched = funcmatch.match(otherline)
                cmatched = classmatch.match(otherline)
                if mmatched and len(mmatched.group(1)) < whitespace:
                    reply("In method %s()" % mmatched.group(2))
                elif fmatched and len(fmatched.group(1)) < whitespace:
                    reply("In function %s()" % fmatched.group(2))
                elif cmatched and len(cmatched.group(1)) < whitespace:
                    reply("In class %s" % cmatched.group(2))

                if wslen(otherline) < whitespace:
                    # Went down an indent level? Don't match function defs or
                    # class defs at this level anymore
                    whitespace = wslen(otherline)


        # Reply with the link to github anchored at that line number
        url_format = "https://github.com/{user}/{repo}/blob/{branch}/{fname}#L{lineno}"
        reply(short_url(url_format.format(
                    user=user, repo=repo, branch=branch, fname=fname, lineno=lineno)))


class Feed(object):
    def __init__(self, url, channels, gh3):
        self.url = url
        self.channels = channels
        self.gh3 = gh3

        # Go ahead and do the initial fetch to see the most recent entry
        # Store lastupdate as a string, lexographic ordering should work just
        # fine. No need to parse the date.
        events = self._fetch()
        self.lastupdate = events[0]['created_at']

    def _fetch(self):
        return self.gh3.query(self.url)

    def get_new_events(self):
        newevents = []
        try:
            allevents = self._fetch()
        except urllib2.HTTPError, e:
            return []


        for event in allevents:
            if event['created_at'] > self.lastupdate:
                newevents.append(event)

        self.lastupdate = allevents[0]['created_at']

        newevents.reverse()
        return newevents

    # So these items can be added to sets properly
    def __hash__(self):
        return hash(self.url)
    def __eq__(self, other):
        return self.url == other.url

    def __str__(self):
        return "<Feed for %s in channels %r>" % (self.url, self.channels)


class GitHubEventMonitorV3(PollPlugin):
    """Monitors one or more GitHub event feeds from version 3 of their api
    described here:

        http://developer.github.com/v3/events/

    """

    poll_interval = 60
    
    @PollPlugin.config_types(feedmap=ET.Element)
    def __init__(self, core, feedmap=None):
        super(GitHubEventMonitorV3, self).__init__(core)

        self.gh3 = MiniGithubAPI()
        
        # Maps feed urls to Feed objects
        self.feeds = {}

        if feedmap == None:
            feedmap = []
        for el in feedmap:
            if not el.tag.lower() == 'feed':
                raise ConfigurationError('feedmap must contain feed tags')
            channel = el.get('channel', None)
            feed_url = el.text
            if not channel or not feed_url:
                raise ConfigurationError('invalid feed tag')
            
            if not feed_url in self.feeds:
                self.feeds[feed_url] = Feed(feed_url, [channel], gh3=self.gh3)
            else:
                self.feeds[feed_url].channels.append(channel)

    def poll(self):
        """Called every poll_interval seconds. Also we should yield every once
        in a while to let the queue process

        """
        event_types = {
                'PushEvent': self._handle_push_event,
                }

        for feed in self.feeds.itervalues():
            for event in feed.get_new_events():
                # Call to the appropriate event handler
                if event['type'] in event_types:
                    reply = event_types[event['type']](event)
                    if reply:
                        for chan in feed.channels:
                            self.parent.send_outgoing(chan, reply)
            yield

    def _handle_push_event(self, event):
        payload = event['payload']
        # Ignore size zero pushes (which can happen e.g. doing a re-wind push
        # that doesn't push any new commits but sets the branch to a different
        # already-existing commit
        numcommits = payload['size']
        if numcommits < 1:
            return

        if numcommits == 1:
            # Handle this specially. Print out a bit from the commit message.
            commit = payload['commits'][0]
            commitmsg = commit['message'].split("\n")[0]
            branch = event['repo']['name']
            pusher = event['actor']['login']
            if len(commitmsg) >= 80:
                commitmsg = commitmsg[:76] + "..."
            url = "https://github.com/%s/commit/%s" % (event['repo']['name'], commit['sha'])
            replystr = "%s pushed to %s: \"%s\" %s" % (pusher, branch, commitmsg, _short_url(url))
        else:
            # Pushed a number of commits at once.
            branch = event['repo']['name']
            pusher = event['actor']['login']
            
            # We need to find the first commit in the series, so we can find
            # its parent, since for the compare we want the range from the
            # first commit's parent to the last commit.
            firstcommit = self.gh3.query(payload['commits'][0]['url'])

            url = "https://github.com/%s/compare/%s...%s" % (event['repo']['name'],
                    firstcommit['parents'][0]['sha'],
                    payload['commits'][-1]['sha'],
                    )
            replystr = "%s pushed %s commits to %s %s" % (pusher, numcommits, branch, _short_url(url))

        return replystr
