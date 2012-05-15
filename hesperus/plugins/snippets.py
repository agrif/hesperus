from hesperus.plugin import CommandPlugin
import re
import pickle

class SnippetPlugin(CommandPlugin):
    _data = {}

    @CommandPlugin.config_types(persist_file=str)
    def __init__(self, core, persist_file):
        self._persist_file = persist_file
        self.load_data()
    @CommandPlugin.register_command(r'snip(?:pet)?\s+(\w+)(\s+(.*))')
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
                reply('%s said: %s', (s[0], s[1]))


    def load_data(self):
        try:
            pf = open(self._persist_file, 'r')
        except IOError:
            pass
        else:
            self._data.update(pickle.load(pf))

    def save_data(self):
        try:
            pf = open(self._persist_file, 'w+')
        except IOError:
            pass
        else:
            pickle.dump(self._persist_file, pf)
