from hesperus.plugin import CommandPlugin
from ..core import ConfigurationError, ET
from ..shorturl import short_url

class BookmarksPlugin(CommandPlugin):
    @CommandPlugin.config_types(bookmarks = ET.Element)
    def __init__(self, core, bookmarks=None):
        super(CommandPlugin, self).__init__(core)
        
        self.bookmarks = {}
        
        if bookmarks == None:
            bookmarks = []
        for el in bookmarks:
            if not el.tag.lower() == 'bookmark':
                raise ConfigurationError('bookmarks must contain bookmark tags')
            names = el.get('names', None)
            if names == None:
                raise ConfigurationError('bookmark tags must have a names attribute')
            url = short_url(el.text.strip())
            
            for name in names.split(","):
                self.bookmarks[name.lower()] = url
        
    @CommandPlugin.register_command(r"(\S+)")
    def bookmark_command(self, chans, match, direct, reply):
        cmd = match.group(1).lower()
        if not cmd in self.bookmarks:
            return
        reply("\"%s\": %s" % (cmd, self.bookmarks[cmd]))
