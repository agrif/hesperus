from ..plugin import CommandPlugin
import os.path
import json
import random

class EveGenerator(object):
    def __init__(self, path):
        self._prefixes = self._load_stats(path, 'prefixes')
        self._cores = self._load_stats(path, 'cores')
        self._suffixes = self._load_stats(path, 'suffixes')

    def _load_stats(self, path, base):
        grams = self._load_json(path, base, '1grams')
        grams = list(grams.items())
        grams.sort(key=lambda t: t[1], reverse=True)
        grams_total = sum(t[1] for t in grams)
        lengths = self._load_json(path, base, 'lengths')
        lengths = [(int(i), w) for i, w in lengths.items()]
        lengths.sort(key=lambda t: t[1], reverse=True)
        lengths_total = sum(t[1] for t in lengths)
        ordered = self._load_json(path, base, 'ordered')
        orders = {k: i for i, k in enumerate(ordered)}
        return {'1grams': grams, 'lengths': lengths, 'orders': orders, 'lengths_total': lengths_total, '1grams_total': grams_total}

    def _load_json(self, path, base, ext):
        fullpath = os.path.join(path, '.'.join([base, ext, 'json']))
        with open(fullpath, 'r') as f:
            return json.load(f)

    def _weighted_choice(self, choices, total):
        i = random.uniform(0, total)
        for choice, weight in choices:
            i -= weight
            if i <= 0:
                return choice
        return choices[-1][0]

    def _generate_part(self, stats):
        length = self._weighted_choice(stats['lengths'], stats['lengths_total'])
        ret = []
        while len(ret) < length:
            w = self._weighted_choice(stats['1grams'], stats['1grams_total'])
            if w in ret:
                continue
            ret.append(w)
        ret.sort(key=lambda w: stats['orders'][w])
        return ret

    def generate(self, tn):
        p = self._generate_part(self._prefixes)
        c = self._generate_part(self._cores)
        s = self._generate_part(self._suffixes)

        if '-' in p:
            p.remove('-')
            p.append('-')
        if '-' in s:
            s.remove('-')
            s.insert(0, '-')
        
        return (u' '.join(p + c + s)).encode('utf-8')

class EveNamePlugin(CommandPlugin):
    @CommandPlugin.config_types(data=str)
    def __init__(self, core, data):
        super(EveNamePlugin, self).__init__(core)
        self._generator = EveGenerator(data)

    @CommandPlugin.register_command(r"(?:itemname|eve|evename|eveitem|eveitemname)")
    def generate(self, chans, name, match, direct, reply):
        reply(self._generator.generate('Whoopsie!'))
