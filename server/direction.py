"""Validação das informações narrativas e das opções da mesa."""
FIELDS = ('origin', 'motivation', 'fear', 'bonds', 'secret', 'quest')


def personality(value):
    value = value if isinstance(value, dict) else {}
    result = {k: value.get(k, '').strip()[:600] if isinstance(value.get(k), str) else '' for k in FIELDS}
    result['status'] = value.get('status') if value.get('status') in ('pending', 'approved', 'completed') else 'pending'
    return result


def campaign_settings(value, previous=None):
    result = dict(previous or {'artifice': True, 'tensionEnabled': False, 'tensionDC': 12})
    value = value if isinstance(value, dict) else {}
    for key in ('artifice', 'tensionEnabled'):
        if key in value and isinstance(value[key], bool):
            result[key] = value[key]
    if 'tensionDC' in value:
        dc = value['tensionDC']
        if isinstance(dc, int) and not isinstance(dc, bool):
            result['tensionDC'] = max(8, min(16, dc))
    return result


def edit_personality(hero, value):
    old = personality(hero.get('def', {}).get('personality'))
    new = personality(value)
    # Só a mensagem de aprovação do Mestre pode alterar o estado da missão.
    new['status'] = old['status'] if all(new[k] == old[k] for k in FIELDS) else 'pending'
    hero.setdefault('def', {})['personality'] = new
    return new
