from ..plugin import CommandPlugin

import mpd

class MPDQuery(CommandPlugin):
    @CommandPlugin.config_types(mpdhost=str, mpdport=int, replyprefix=str, replypostfix=str)
    def __init__(self, core, mpdhost, replyprefix, replypostfix, mpdport=6600):
        super(MPDQuery, self).__init__(core)

        self.mpdhost = mpdhost
        self.mpdport = mpdport
        self.replyprefix = replyprefix
        self.replypostfix = replypostfix

    @CommandPlugin.register_command("music")
    def music(self, chans, name, match, direct, reply):
        client = mpd.MPDClient()
        client.connect(self.mpdhost, self.mpdport)
        songinfo = client.currentsong()
        client.disconnect()

        reply("%s %s - %s - %s. %s" % (
            self.replyprefix,
            songinfo['title'],
            songinfo['artist'],
            songinfo['album'],
            self.replypostfix,
            ))
