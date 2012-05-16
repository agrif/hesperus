from hesperus.plugin import CommandPlugin
import re
import json
import random

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
            reply('Today I learned about "{thing}"'.format(thing=match.group(1)))
        else:
            try:
                s = self._data[match.group(1)]
            except KeyError:
                key = match.group(1)
                if key == 'list':
                    reply('I know these things: {snippets}'.format(snippets=', '.join(self._data.keys())))
                elif key == 'save':
                    self.save_data()
                    reply('Sure, let me just find a pen')
                elif key == 'reload':
                    self.load_data()
                    reply('Getting a sense of deja vu here...')
                elif key == 'random':
                    reply('"{snippet[1]}" -- {snippet[0]}'.format(
                        snippet=self._data[self._data.keys()[random.randint(0,len(self._data)-1)]]))
                else:
                    reply('I don\'t know anything about "{thing}"'.format(thing=key))
            else:
                reply('"{snippet[1]}" -- {snippet[0]}'.format(snippet=s))


    def load_data(self):
        try:
            with open(self._persist_file, 'rb') as pf:
                self._data.update(json.load(pf))
        except IOError:
            pass

    def save_data(self):
        with open(self._persist_file, 'wb') as pf:
            json.dump(self._data, pf, indent=4)
