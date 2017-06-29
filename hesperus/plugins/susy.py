import random
from ..plugin import PassivePlugin
from ..core import ET

class Susy(PassivePlugin):
    MESSAGE = "{stem}ino, supersymmetric partner of the {stem}on"

    WORDS = set('lino vino kino fino wino dino amino rhino chino imino casino domino albino merino panino pepino ammino arsino latino ladino bambino cassino porcino sordino amorino mestino palomino pecorino cioppino zechhino crostino campesino solferino andantino gravitino sopranino carbamino cipollino cappuccino maraschino concertino langostino baldachino'.split())

    PARTICLES = set('electron neutron positron muon photon boson proton neutron gluon graviton'.split())
    
    @PassivePlugin.config_types(chance=float)
    def __init__(self, core, chance=1.0, *args):
        super(Susy, self).__init__(core, *args)
        self._chance = chance

    @PassivePlugin.register_pattern(r'(?i)\b([a-z]+)inos?\b')
    def susy(self, match, reply):
        if random.random() > self._chance:
            return
        stem = match.group(1).lower()

        if stem + 'ino' in self.WORDS:
            return
        if stem + 'on' in self.PARTICLES:
            return
        if stem.startswith('anti') and stem[4:].lstrip('-') + 'on' in self.PARTICLES:
            return
        
        reply(self.MESSAGE.format(stem=stem))
