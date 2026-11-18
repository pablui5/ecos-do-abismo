"""A campanha usa o mesmo catálogo estático do cliente e transições verificadas."""
import json
import re
from pathlib import Path
DATA = json.loads(re.search(r'const DATA = (.*?);\n', (Path(__file__).resolve().parents[1] / 'public/campaign.js').read_text(encoding='utf-8')).group(1))


def initial():
    return {'active': False, 'step': 0, 'completed': False, 'ending': None, 'side': {}, 'journal': [], 'revision': 0}


def normalize(value):
    s = initial()
    if not isinstance(value, dict):
        return s
    s['active'] = value.get('active') is True
    n = value.get('step', 0)
    s['step'] = max(0, min(len(DATA['steps']), n)) if type(n) is int else 0
    s['completed'] = value.get('completed') is True and s['step'] == len(DATA['steps'])
    ending = value.get('ending')
    s['ending'] = ending if isinstance(ending, str) and ending in DATA['endings'] else None
    sides = value.get('side') if isinstance(value.get('side'), dict) else {}
    s['side'] = {q['id']: sides[q['id']] if sides.get(q['id']) in ('active', 'completed') else 'available' for q in DATA['side']}
    journal = value.get('journal', [])
    s['journal'] = [x[:1200] for x in journal if isinstance(x, str)][-30:] if isinstance(journal, list) else []
    revision = value.get('revision', 0)
    s['revision'] = max(0, revision) if type(revision) is int else 0
    return s


def objective(s, ident):
    if ident == 'main':
        return DATA['steps'][s['step']] if s['step'] < len(DATA['steps']) else None
    return next((q for q in DATA['side'] if q['id'] == ident), None)


def advance(state, ident, evidence, ending=None):
    s = normalize(state)
    q = objective(s, ident)
    if not s['active'] or not q or (ident == 'main' and s['completed']) or (ident != 'main' and s['side'].get(ident) != 'active'):
        return None, 'Esta missão não está ativa.'
    if evidence.get('area') != q['area'] or evidence.get('mode') != 'explore':
        return None, 'Viaje ao objetivo e conclua o combate.'
    if not evidence.get('alive') or evidence.get('down'):
        return None, 'O protagonista precisa estar consciente.'
    c, r = evidence.get('c'), evidence.get('r')
    if type(c) is not int or type(r) is not int or max(abs(c-q['c']), abs(r-q['r'])) > 1:
        return None, 'Aproxime-se do objetivo.'
    kills = evidence.get('kills', 0)
    if type(kills) is not int or kills < q['kills'] or (q.get('boss') and not evidence.get('boss')):
        return None, 'Os guardiões do objetivo ainda não foram vencidos.'
    if q.get('boss') and (not isinstance(ending, str) or ending not in DATA['endings']):
        return None, 'Escolha o destino do selo.'
    s['journal'].append(q['title'] + ': ' + q['dialogue'])
    s['revision'] += 1
    if ident == 'main':
        s['step'] += 1
        s['completed'] = s['step'] == len(DATA['steps'])
        if s['completed']:
            s['ending'] = ending
            s['journal'].append(DATA['endings'][ending]['text'])
    else:
        s['side'][ident] = 'completed'
    return {'state': s, 'gold': q['gold'], 'title': q['title']}, None
