
def _ansi_sgr(s, *settings):
    return '\033['+';'.join(map(str, settings))+'m' + s + '\033[0m'

colored_map = {
    # foregrounds
    'black' : 30,
    'red' : 31,
    'green' : 32,
    'yellow' : 33,
    'blue' : 34,
    'magenta' : 35,
    'cyan' : 36,
    'white' : 37,
    
    # settings
    'bold' : 1,
}

def colored(txt, *attrs):
    sgr_settings = []
    for attr in attrs:
        attr = attr.lower()
        if not attr in colored_map:
            raise ValueError('%s is not a valid text attribute' % (attr,))
        sgr_settings.append(colored_map[attr])
    return _ansi_sgr(txt, *sgr_settings)
