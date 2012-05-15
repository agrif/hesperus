from hesperus.plugin import CommandPlugin
import re
import json

class SnippetPlugin(CommandPlugin):
    _data = {}

    @CommandPlugin.config_types(persist_file=str)
    def __init__(self, core, persist_file):
        super(SnippetPlugin, self).__init__(core)
        self._persist_file = persist_file
        self.load_data()
    @CommandPlugin.register_command(r'snip(?:pet)?\s+(\w+)(?:\s+(.*))?')
    def snippet_command(self, chans, name, match, direct, reply):
        if match.group(2):
            self._data[match.group(1)] = (name, match.group(2))
            self.save_data()
            reply('Saved snippet to key: %s' % match.group(1))
        else:
            try:
                s = self._data[match.group(1)]
            except KeyError:
                reply('I don\'t remember anyone saying anything about that')
            else:
                reply('%s said: %s' % (s[0], s[1]))


    def load_data(self):
        try:
            with open(self._persist_file, 'rb') as pf:
                self._data.update(json.load(pf))
        except IOError:
            pass

    def save_data(self):
        with open(self._persist_file, 'wb') as pf:
            json.dump(self._data, pf, indent=4)
