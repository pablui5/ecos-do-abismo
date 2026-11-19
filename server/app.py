"""Servidor de Ecos do Abismo.

- Entrega o jogo (pasta public/) por HTTP.
- Mantém salas multijogador por WebSocket em /ws.
- Gera os dados no servidor e valida cada rolagem informada pelo Mestre.
- É a autoridade do inventário: equipar, comprar, vender, baú e trocas
  (com confirmação dos dois lados) passam por aqui, sem duplicar nem perder itens.
- Salva as salas no banco (PostgreSQL no Render, SQLite no PC).

Só usa a biblioteca padrão do Python (mais psycopg quando houver PostgreSQL).
"""
import asyncio
import base64
import hashlib
import json
import mimetypes
import os
import random
import re
import secrets
import struct
import time
from pathlib import Path

from db import Store

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / 'public'
WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
MAX_MSG = 2 * 1024 * 1024
RNG = random.SystemRandom()
CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

# ---------------------------------------------------------------------------
# Dados do arsenal: lidos do próprio cliente, para preço e mãos baterem sempre
# ---------------------------------------------------------------------------
def load_arsenal():
    html = (PUBLIC / 'index.html').read_text(encoding='utf-8')
    m = re.search(r'const ARSENAL = (\{.*?\n\});', html, re.S)
    js = m.group(1)
    js = re.sub(r'^(\s*)(\w+):\[', r'\1"\2":[', js, flags=re.M)
    js = js.replace("'", '"')
    js = re.sub(r'([\[,]\s*)\.(\d)', r'\g<1>0.\2', js)
    js = re.sub(r',\s*([\]}])', r'\1', js)
    data = json.loads(js)
    weapons = {}
    for fam, rows in data.items():
        for i, row in enumerate(rows):
            name, dice, typ, hands, w, p, props = row[:7]
            weapons[f'{fam}_{i}'] = {'n': name, 'fam': fam, 'hands': hands, 'p': p, 'props': props.split()}
    return weapons

WEAPONS = load_arsenal()
SHIELDS = {'escudo': {'n': 'Escudo', 'p': 10}, 'broquel': {'n': 'Broquel', 'p': 8}}
AMMO = {'flecha': (20, 1), 'virote': (20, 1), 'bala': (10, 3), 'frasco': (4, 6)}
POTION_PRICE = 10
assert len(WEAPONS) == 120, f'arsenal com {len(WEAPONS)} armas'

def item_def(it):
    return WEAPONS.get(it.get('wid')) or SHIELDS.get(it.get('wid'))

def is_shield(it):
    return it.get('wid') in SHIELDS

def new_item(wid):
    it = {'uid': 's' + secrets.token_hex(5), 'wid': wid}
    d = WEAPONS.get(wid)
    if d:
        props = d['props']
        if any(p in props for p in ('recarga', 'carregamento', 'pistao')):
            it['loaded'] = True
        for p in props:
            if p.startswith('rep:'):
                it['mag'] = int(p[4:])
            if p.startswith('q:'):
                it['qty'] = int(p[2:])
    return it

# ---------------------------------------------------------------------------
# Rolagens no servidor
# ---------------------------------------------------------------------------
DIE_SIDES = {4, 6, 8, 10, 12, 20, 100}

def roll_expression(expr):
    s = re.sub(r'\s', '', str(expr)).lower()
    if not s or not re.fullmatch(r'[0-9d+\-]+', s) or len(s) > 40:
        return None
    total, parts, first = 0, [], None
    for term in re.findall(r'[+-]?[^+-]+', s):
        sign = -1 if term[0] == '-' else 1
        body = term.lstrip('+-')
        m = re.fullmatch(r'(\d*)d(\d+)', body)
        if m:
            n, sides = int(m.group(1) or 1), int(m.group(2))
            if sides not in DIE_SIDES or not 1 <= n <= 40:
                return None
            rolls = [RNG.randint(1, sides) for _ in range(n)]
            if first is None:
                first = (rolls[0], sides)
            total += sign * sum(rolls)
            parts.append(f"{'− ' if sign < 0 else ('+ ' if parts else '')}{n}d{sides} [{', '.join(map(str, rolls))}]")
        elif body.isdigit():
            total += sign * int(body)
            parts.append(f"{'−' if sign < 0 else '+'} {body}")
        else:
            return None
    return {'total': total, 'detail': ' '.join(parts) + f' = {total}', 'face': first[0] if first else total, 'die': first[1] if first else 0}

# ---------------------------------------------------------------------------
# Salas
# ---------------------------------------------------------------------------
store = None
rooms = {}


class Conn:
    def __init__(self, writer):
        self.writer = writer
        self.lock = asyncio.Lock()
        self.room = None
        self.pid = None
        self.open = True

    async def send(self, obj):
        if not self.open:
            return
        data = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        try:
            async with self.lock:
                self.writer.write(ws_frame(data))
                await self.writer.drain()
        except Exception:
            self.open = False


class Room:
    def __init__(self, code, data=None):
        self.code = code
        d = data or {}
        self.players = d.get('players', {})          # pid -> {name, token, role}
        self.host = d.get('host')
        self.party = d.get('party', [])              # heróis: inventário, conjuntos, ouro...
        self.stash = d.get('stash', [])
        self.log = d.get('log', [])[-300:]
        self.settings = d.get('settings', {'artifice': True})
        self.snap = d.get('snap')
        self.mode = d.get('mode', 'explore')
        self.trades = {}
        self.conns = {}                              # pid -> Conn
        self.tape = []
        self.tape_start = d.get('tape_next', 0)
        self.tape_used = self.tape_start
        self.created = d.get('created', time.time())
        self.dirty = False

    def to_data(self):
        return {'players': self.players, 'host': self.host, 'party': self.party, 'stash': self.stash, 'log': self.log[-300:],
                'settings': self.settings, 'snap': self.snap, 'mode': self.mode, 'created': self.created,
                'tape_next': self.tape_start + len(self.tape)}

    def public(self):
        return {'code': self.code, 'host': self.host, 'party': self.party, 'stash': self.stash, 'settings': self.settings,
                'players': [{'pid': p, 'name': v['name'], 'role': v['role'], 'online': p in self.conns} for p, v in self.players.items()],
                'trades': list(self.trades.values()), 'log': self.log[-80:]}

    async def broadcast(self, obj, exclude=None, only_host=False):
        for pid, c in list(self.conns.items()):
            if pid == exclude:
                continue
            if only_host and pid != self.host:
                continue
            await c.send(obj)

    async def push_party(self):
        self.dirty = True
        await self.broadcast({'t': 'party', 'party': self.party, 'stash': self.stash, 'trades': list(self.trades.values())})

    async def push_players(self):
        await self.broadcast({'t': 'players', 'players': self.public()['players'], 'host': self.host})

    def hero(self, hid):
        return next((h for h in self.party if h.get('id') == hid), None)

    def can_control(self, pid, hid):
        h = self.hero(hid)
        return bool(h) and (pid == self.host or h.get('owner') == pid)

    def fill_tape(self, n=512):
        vals = [RNG.getrandbits(32) for _ in range(n)]
        start = self.tape_start + len(self.tape)
        self.tape.extend(vals)
        return start, vals

    def check_roll(self, used):
        """Confere se cada dado usado pelo Mestre saiu da fita gerada aqui, em ordem."""
        for i, n, v in used:
            idx = i - self.tape_start
            if not (0 <= idx < len(self.tape)) or i < self.tape_used or n < 1:
                return False
            if self.tape[idx] % n + 1 != v:
                return False
            self.tape_used = i + 1
        return True


def new_code():
    while True:
        code = ''.join(RNG.choice(CODE_CHARS) for _ in range(6))
        if code not in rooms and not store.load_room(code):
            return code


async def get_room(code):
    code = (code or '').strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{6}', code):
        return None
    if code in rooms:
        return rooms[code]
    data = await asyncio.to_thread(store.load_room, code)
    if data:
        rooms[code] = Room(code, data)
        return rooms[code]
    return None


async def saver():
    while True:
        await asyncio.sleep(2)
        for room in list(rooms.values()):
            if room.dirty:
                room.dirty = False
                try:
                    await asyncio.to_thread(store.save_room, room.code, room.to_data())
                except Exception as e:
                    print('erro ao salvar sala', room.code, e)
                    room.dirty = True


def clean_name(s):
    s = re.sub(r'[\x00-\x1f<>]', '', str(s or '')).strip()
    return s[:24] or 'Aventureiro'


# ---------------------------------------------------------------------------
# Inventário: regras conferidas no servidor
# ---------------------------------------------------------------------------
def find_item(hero, uid):
    return next((i for i in hero.get('inv', []) if i.get('uid') == uid), None)

def unequip_everywhere(hero, uid):
    for s in hero.get('sets', []):
        if s.get('main') == uid:
            s['main'] = None
        if s.get('off') == uid:
            s['off'] = None

def remove_item(hero, uid):
    it = find_item(hero, uid)
    if it:
        unequip_everywhere(hero, uid)
        hero['inv'] = [i for i in hero['inv'] if i.get('uid') != uid]
    return it

def slot_error(hero, it, set_idx, slot):
    d = item_def(it)
    if not d:
        return 'Item inválido.'
    st = hero['sets'][set_idx]
    if slot == 'off':
        if not is_shield(it) and d.get('hands') != 1:
            return 'Armas de duas mãos só vão na mão principal.'
        main = find_item(hero, st.get('main'))
        if main and not is_shield(main) and item_def(main) and item_def(main).get('hands') == 2:
            return 'A mão principal está com uma arma de duas mãos.'
    elif slot == 'main':
        if is_shield(it):
            return 'Escudos vão na mão secundária.'
    else:
        return 'Espaço inválido.'
    return ''


async def handle_inventory(room, conn, m):
    t = m.get('t')
    pid = conn.pid
    if t == 'tradeConfirm':
        tr = room.trades.get(m.get('id'))
        if not tr:
            return 'Essa troca não existe mais.'
        side = 'a' if room.can_control(pid, tr['a']) and m.get('side') != 'b' else 'b' if room.can_control(pid, tr['b']) else None
        if m.get('side') in ('a', 'b') and room.can_control(pid, tr[m['side']]):
            side = m['side']
        if not side:
            return 'Você não controla nenhum dos heróis desta troca.'
        tr['ok_' + side] = True
        if tr.get('ok_a') and tr.get('ok_b'):
            return await execute_trade(room, tr)
        await room.push_party()
        return None
    if t == 'tradeCancel':
        tr = room.trades.pop(m.get('id'), None)
        if tr:
            await room.push_party()
        return None
    hid = m.get('hero')
    if not room.can_control(pid, hid):
        return 'Você não controla esse herói.'
    hero = room.hero(hid)
    if room.mode == 'combat' and t not in ('tradePropose',):
        return 'Em combate, trocas de equipamento passam pelo turno (ação bônus).'
    if t == 'equip':
        it = find_item(hero, m.get('uid'))
        si, slot = int(m.get('set', 0)), m.get('slot')
        if not it or si not in (0, 1):
            return 'Item não encontrado.'
        err = slot_error(hero, it, si, slot)
        if err:
            return err
        st = hero['sets'][si]
        if st.get('main') == it['uid']:
            st['main'] = None
        if st.get('off') == it['uid']:
            st['off'] = None
        st[slot] = it['uid']
        d = item_def(it)
        if slot == 'main' and not is_shield(it) and d.get('hands') == 2:
            st['off'] = None
    elif t == 'unequip':
        si, slot = int(m.get('set', 0)), m.get('slot')
        if si in (0, 1) and slot in ('main', 'off'):
            hero['sets'][si][slot] = None
    elif t == 'useSet':
        hero['set'] = 1 if int(m.get('set', 0)) == 1 else 0
    elif t == 'stashPut':
        it = remove_item(hero, m.get('uid'))
        if not it:
            return 'Item não encontrado.'
        room.stash.append(it)
    elif t == 'stashTake':
        it = next((i for i in room.stash if i.get('uid') == m.get('uid')), None)
        if not it:
            return 'Esse item já saiu do baú.'
        room.stash = [i for i in room.stash if i.get('uid') != it['uid']]
        hero['inv'].append(it)
    elif t == 'buy':
        kind, key = m.get('kind'), m.get('id')
        if kind == 'weapon':
            d = WEAPONS.get(key)
            if not d or (d['fam'] == 'artifice' and not room.settings.get('artifice', True)):
                return 'Arma indisponível.'
            price, add = d['p'], lambda: hero['inv'].append(new_item(key))
        elif kind == 'shield':
            d = SHIELDS.get(key)
            if not d:
                return 'Escudo indisponível.'
            price, add = d['p'], lambda: hero['inv'].append(new_item(key))
        elif kind == 'ammo':
            if key not in AMMO:
                return 'Munição indisponível.'
            pack, price = AMMO[key]
            def add():
                hero['ammo'][key] = hero['ammo'].get(key, 0) + pack
        elif kind == 'potion':
            price = POTION_PRICE
            def add():
                hero['items']['pocao'] = hero['items'].get('pocao', 0) + 1
        else:
            return 'Compra inválida.'
        if hero.get('gold', 0) < price:
            return 'Moedas insuficientes.'
        hero['gold'] -= price
        add()
    elif t == 'sell':
        it = find_item(hero, m.get('uid'))
        if not it:
            return 'Item não encontrado.'
        if any(s.get('main') == it['uid'] or s.get('off') == it['uid'] for s in hero['sets']):
            return 'Tire o item do conjunto antes de vender.'
        remove_item(hero, it['uid'])
        hero['gold'] += (item_def(it) or {'p': 0})['p'] // 2
    elif t == 'tradePropose':
        if room.mode == 'combat':
            return 'Trocas entre heróis só fora de combate.'
        other = room.hero(m.get('with'))
        if not other or other is hero:
            return 'Escolha outro herói.'
        give, take = list(dict.fromkeys(m.get('give', []))), list(dict.fromkeys(m.get('take', [])))
        if any(not find_item(hero, u) for u in give) or any(not find_item(other, u) for u in take):
            return 'Algum item não pertence a quem oferece.'
        ga, gb = max(0, int(m.get('goldGive', 0))), max(0, int(m.get('goldTake', 0)))
        if ga > hero.get('gold', 0) or gb > other.get('gold', 0):
            return 'Moedas insuficientes.'
        if not give and not take and not ga and not gb:
            return 'A troca está vazia.'
        tid = 't' + secrets.token_hex(4)
        room.trades[tid] = {'id': tid, 'a': hid, 'b': other['id'], 'give': give, 'take': take, 'goldA': ga, 'goldB': gb, 'ok_a': True, 'ok_b': room.can_control(pid, other['id']) and m.get('both', False)}
        if room.trades[tid]['ok_b']:
            return await execute_trade(room, room.trades[tid])
    else:
        return 'Operação desconhecida.'
    await room.push_party()
    return None


async def execute_trade(room, tr):
    a, b = room.hero(tr['a']), room.hero(tr['b'])
    room.trades.pop(tr['id'], None)
    if not a or not b or any(not find_item(a, u) for u in tr['give']) or any(not find_item(b, u) for u in tr['take']) \
            or tr['goldA'] > a.get('gold', 0) or tr['goldB'] > b.get('gold', 0):
        await room.push_party()
        return 'Os itens ou moedas mudaram antes da confirmação. Troca cancelada.'
    moved_a = [remove_item(a, u) for u in tr['give']]
    moved_b = [remove_item(b, u) for u in tr['take']]
    a['inv'].extend(moved_b)
    b['inv'].extend(moved_a)
    a['gold'] += tr['goldB'] - tr['goldA']
    b['gold'] += tr['goldA'] - tr['goldB']
    entry = {'text': f"Troca concluída entre {a['def']['name']} e {b['def']['name']}.", 'cls': 'sys', 't': time.time() * 1000}
    room.log.append(entry)
    await room.broadcast({'t': 'log', 'entries': [entry]})
    await room.push_party()
    return None


RUNTIME_FIELDS = ('hp', 'xp', 'lvl', 'ammo', 'items', 'mast', 'mp', 'asiPending', 'set')

def merge_runtime(room, heroes):
    """O Mestre roda o combate: aceita dele os campos de jogo, nunca a composição do inventário."""
    for rec in heroes or []:
        h = room.hero(rec.get('id'))
        if not h:
            continue
        for k in RUNTIME_FIELDS:
            if k in rec:
                h[k] = rec[k]
        if isinstance(rec.get('def'), dict):
            for k in ('name', 'story', 'asi'):
                if k in rec['def']:
                    h['def'][k] = rec['def'][k]
        if isinstance(rec.get('sets'), list) and len(rec['sets']) == 2:
            uids = {i['uid'] for i in h['inv']}
            ok = all((s.get('main') in uids or s.get('main') is None) and (s.get('off') in uids or s.get('off') is None) for s in rec['sets'])
            if ok:
                h['sets'] = [{'main': s.get('main'), 'off': s.get('off')} for s in rec['sets']]
        states = rec.get('invState') or {}
        for it in h['inv']:
            st = states.get(it['uid'])
            if isinstance(st, dict):
                for k in ('loaded', 'mag', 'qty'):
                    if k in st:
                        it[k] = st[k]


# ---------------------------------------------------------------------------
# Mensagens
# ---------------------------------------------------------------------------
async def on_message(conn, m):
    t = m.get('t')
    room = conn.room
    if t == 'ping':
        return
    if t == 'create':
        code = new_code()
        room = Room(code)
        pid = 'p' + secrets.token_hex(4)
        token = secrets.token_urlsafe(18)
        room.players[pid] = {'name': clean_name(m.get('name')), 'token': token, 'role': 'host'}
        room.host = pid
        room.settings = {'artifice': bool(m.get('settings', {}).get('artifice', True))}
        for i, h in enumerate(m.get('party', [])[:6]):
            h['id'] = h.get('id') or f'h{i}'
            h['owner'] = pid
            h.setdefault('gold', 40); h.setdefault('ammo', {}); h.setdefault('items', {}); h.setdefault('inv', []); h.setdefault('sets', [{'main': None, 'off': None}, {'main': None, 'off': None}])
            room.party.append(h)
        room.stash = m.get('stash', [])[:200]
        rooms[code] = room
        room.dirty = True
        conn.room, conn.pid = room, pid
        room.conns[pid] = conn
        start, vals = room.fill_tape()
        await conn.send({'t': 'joined', 'you': {'pid': pid, 'token': token, 'role': 'host'}, 'room': room.public()})
        await conn.send({'t': 'tape', 'start': start, 'values': vals})
        return
    if t in ('join', 'resume'):
        room = await get_room(m.get('code'))
        if not room:
            return await conn.send({'t': 'error', 'msg': 'Sala não encontrada. Confira o código.'})
        token = m.get('token')
        pid = next((p for p, v in room.players.items() if token and v.get('token') == token), None)
        if not pid:
            if t == 'resume':
                return await conn.send({'t': 'error', 'msg': 'Não foi possível retomar: entre de novo com o código.'})
            pid = 'p' + secrets.token_hex(4)
            token = secrets.token_urlsafe(18)
            room.players[pid] = {'name': clean_name(m.get('name')), 'token': token, 'role': 'player'}
            room.dirty = True
        old = room.conns.get(pid)
        if old and old is not conn:
            old.open = False
        conn.room, conn.pid = room, pid
        room.conns[pid] = conn
        role = room.players[pid]['role']
        await conn.send({'t': 'joined', 'you': {'pid': pid, 'token': room.players[pid]['token'], 'role': role}, 'room': room.public(), 'snap': room.snap,
                         'rolls': list(reversed(await asyncio.to_thread(store.recent_rolls, room.code, 40)))})
        if role == 'host':
            start, vals = room.fill_tape()
            await conn.send({'t': 'tape', 'start': start, 'values': vals})
        await room.push_players()
        return
    if not room or not conn.pid:
        return await conn.send({'t': 'error', 'msg': 'Entre numa sala primeiro.'})
    pid = conn.pid
    is_host = pid == room.host
    if t == 'claim':
        h = room.hero(m.get('hero'))
        if h and (h.get('owner') in (None, room.host) or h.get('owner') not in room.conns or is_host):
            h['owner'] = m.get('pid') if is_host and m.get('pid') in room.players else pid
            await room.push_party()
        return
    if t == 'intent':
        if not room.can_control(pid, m.get('hero')) and not (is_host and m.get('monster')):
            return await conn.send({'t': 'error', 'msg': 'Você não controla esse herói.'})
        if room.host not in room.conns:
            return await conn.send({'t': 'error', 'msg': 'O Mestre está desconectado.'})
        m['from'] = pid
        await room.conns[room.host].send(m)
        return
    if t == 'freeRoll':
        r = roll_expression(m.get('expr'))
        if not r:
            return await conn.send({'t': 'error', 'msg': 'Expressão inválida. Use dados d4, d6, d8, d10, d12, d20 ou d100, como 2d6+3.'})
        secret = bool(m.get('secret')) and is_host
        entry = {'who': room.players[pid]['name'] if not secret else 'Mestre', 'label': f"Rolagem livre {m.get('expr')}", 'die': r['die'], 'rolls': [r['face']], 'total': r['total'],
                 'detail': r['detail'], 'secret': secret, 'valid': True, 'server': True, 't': time.time() * 1000}
        await asyncio.to_thread(store.add_roll, room.code, entry)
        if secret:
            await room.broadcast({'t': 'roll', 'roll': entry}, only_host=True)
            await room.broadcast({'t': 'roll', 'roll': {'who': 'Mestre', 'label': 'rolagem secreta', 'die': r['die'], 'rolls': ['?'], 'total': '?', 'detail': 'O resultado fica com o Mestre.', 'secret': True, 'valid': True, 't': entry['t']}}, exclude=room.host)
        else:
            await room.broadcast({'t': 'roll', 'roll': entry})
        return
    if t in ('equip', 'unequip', 'useSet', 'stashPut', 'stashTake', 'buy', 'sell', 'tradePropose', 'tradeConfirm', 'tradeCancel'):
        err = await handle_inventory(room, conn, m)
        if err:
            await conn.send({'t': 'error', 'msg': err})
        return
    # --- só o Mestre daqui para baixo ---
    if not is_host:
        return await conn.send({'t': 'error', 'msg': 'Só o Mestre pode fazer isso.'})
    if t == 'snap':
        room.snap = m.get('s')
        room.mode = (room.snap or {}).get('mode', room.mode)
        room.dirty = True
        await room.broadcast({'t': 'snap', 's': room.snap}, exclude=pid)
    elif t == 'fx':
        await room.broadcast(m, exclude=pid)
    elif t == 'log':
        entries = m.get('entries', [])[:50]
        room.log.extend(entries)
        room.log = room.log[-300:]
        room.dirty = True
        await room.broadcast({'t': 'log', 'entries': entries}, exclude=pid)
    elif t == 'roll':
        e = m.get('roll') or {}
        used = [u for u in m.get('used', []) if isinstance(u, list) and len(u) == 3]
        e['valid'] = room.check_roll(used) if used else False
        e['server'] = bool(used)
        await asyncio.to_thread(store.add_roll, room.code, e)
        if e.get('secret'):
            return
        await room.broadcast({'t': 'roll', 'roll': e}, exclude=pid)
        if used and not e['valid']:
            await conn.send({'t': 'error', 'msg': 'Uma rolagem não bateu com os dados do servidor e foi marcada como inválida.'})
    elif t == 'tapeMore':
        start, vals = room.fill_tape()
        await conn.send({'t': 'tape', 'start': start, 'values': vals})
    elif t == 'party':
        merge_runtime(room, m.get('heroes'))
        room.dirty = True
        await room.broadcast({'t': 'party', 'party': room.party, 'stash': room.stash, 'trades': list(room.trades.values())}, exclude=pid)
    elif t == 'loot':
        for hid, n in (m.get('gold') or {}).items():
            h = room.hero(hid)
            if h:
                h['gold'] = h.get('gold', 0) + max(0, min(1000, int(n)))
        for hid, n in (m.get('potions') or {}).items():
            h = room.hero(hid)
            if h:
                h['items']['pocao'] = h['items'].get('pocao', 0) + max(0, min(10, int(n)))
        for wid in (m.get('stash') or [])[:10]:
            if wid in WEAPONS or wid in SHIELDS:
                room.stash.append(new_item(wid))
        await room.push_party()
    elif t == 'settings':
        room.settings['artifice'] = bool(m.get('artifice', True))
        room.dirty = True
        await room.broadcast({'t': 'settings', 'settings': room.settings})
    elif t == 'resetParty':
        for rec in m.get('party', [])[:6]:
            h = room.hero(rec.get('id'))
            if h:
                for k in ('def', 'inv', 'sets', 'set', 'gold', 'ammo', 'items', 'mast', 'mp', 'asiPending', 'lvl', 'xp', 'hp'):
                    if k in rec:
                        h[k] = rec[k]
        await room.push_party()


# ---------------------------------------------------------------------------
# HTTP e WebSocket (RFC 6455) com asyncio
# ---------------------------------------------------------------------------
def ws_frame(payload, opcode=1):
    n = len(payload)
    if n < 126:
        head = struct.pack('!BB', 0x80 | opcode, n)
    elif n < 65536:
        head = struct.pack('!BBH', 0x80 | opcode, 126, n)
    else:
        head = struct.pack('!BBQ', 0x80 | opcode, 127, n)
    return head + payload


async def ws_read(reader):
    chunks, opcode = [], None
    while True:
        b1, b2 = await reader.readexactly(2)
        fin, op = b1 & 0x80, b1 & 0x0F
        masked, ln = b2 & 0x80, b2 & 0x7F
        if ln == 126:
            ln = struct.unpack('!H', await reader.readexactly(2))[0]
        elif ln == 127:
            ln = struct.unpack('!Q', await reader.readexactly(8))[0]
        if ln > MAX_MSG:
            raise ValueError('mensagem grande demais')
        mask = await reader.readexactly(4) if masked else b''
        data = await reader.readexactly(ln)
        if masked and ln:
            key = (mask * (ln // 4 + 1))[:ln]
            data = (int.from_bytes(data, 'big') ^ int.from_bytes(key, 'big')).to_bytes(ln, 'big')
        if op >= 8:
            return op, data
        if op != 0:
            opcode = op
        chunks.append(data)
        if sum(len(c) for c in chunks) > MAX_MSG:
            raise ValueError('mensagem grande demais')
        if fin:
            return opcode, b''.join(chunks)


async def websocket_session(reader, writer):
    conn = Conn(writer)
    try:
        while conn.open:
            op, data = await ws_read(reader)
            if op == 8:
                break
            if op == 9:
                async with conn.lock:
                    writer.write(ws_frame(data, 10))
                    await writer.drain()
                continue
            if op != 1:
                continue
            try:
                m = json.loads(data.decode('utf-8'))
            except Exception:
                continue
            if isinstance(m, dict):
                try:
                    await on_message(conn, m)
                except Exception as e:
                    print('erro na mensagem', m.get('t'), repr(e))
                    await conn.send({'t': 'error', 'msg': 'O servidor não conseguiu processar essa ação.'})
    except (asyncio.IncompleteReadError, ConnectionError, ValueError):
        pass
    finally:
        conn.open = False
        room = conn.room
        if room and room.conns.get(conn.pid) is conn:
            del room.conns[conn.pid]
            await room.push_players()
        try:
            writer.close()
        except Exception:
            pass


def http_response(writer, status, body=b'', ctype='text/plain; charset=utf-8', head_only=False, extra=''):
    reason = {200: 'OK', 304: 'Not Modified', 400: 'Bad Request', 404: 'Not Found', 405: 'Method Not Allowed'}.get(status, 'OK')
    headers = f'HTTP/1.1 {status} {reason}\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\nConnection: close\r\nX-Content-Type-Options: nosniff\r\n{extra}\r\n'
    writer.write(headers.encode('latin-1') + (b'' if head_only else body))


async def handle_client(reader, writer):
    try:
        raw = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), timeout=15)
    except Exception:
        writer.close()
        return
    if len(raw) > 16384:
        writer.close()
        return
    lines = raw.decode('latin-1').split('\r\n')
    try:
        method, target, _ = lines[0].split(' ', 2)
    except ValueError:
        writer.close()
        return
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            k, v = line.split(':', 1)
            headers[k.strip().lower()] = v.strip()
    path = target.split('?', 1)[0]
    if path == '/ws' and 'websocket' in headers.get('upgrade', '').lower():
        key = headers.get('sec-websocket-key', '')
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        writer.write(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                      f'Sec-WebSocket-Accept: {accept}\r\n\r\n').encode())
        await writer.drain()
        await websocket_session(reader, writer)
        return
    if method not in ('GET', 'HEAD'):
        http_response(writer, 405)
    elif path == '/health':
        http_response(writer, 200, json.dumps({'ok': True, 'db': store.kind, 'rooms': len(rooms), 'weapons': len(WEAPONS)}).encode(), 'application/json', method == 'HEAD')
    else:
        rel = 'index.html' if path in ('/', '') else path.lstrip('/')
        file = (PUBLIC / rel).resolve()
        if PUBLIC.resolve() not in file.parents or not file.is_file():
            http_response(writer, 404, b'Nada aqui.', head_only=method == 'HEAD')
        else:
            ctype = mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
            if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'):
                ctype += '; charset=utf-8'
            http_response(writer, 200, file.read_bytes(), ctype, method == 'HEAD', 'Cache-Control: no-cache\r\n')
    try:
        await writer.drain()
    finally:
        writer.close()


async def main():
    global store
    store = Store()
    port = int(os.environ.get('PORT', '8000'))
    host = os.environ.get('HOST', '0.0.0.0')
    server = await asyncio.start_server(handle_client, host, port, limit=MAX_MSG + 1024)
    asyncio.create_task(saver())
    print(f'Ecos do Abismo em http://{"localhost" if host == "0.0.0.0" else host}:{port} · banco: {store.kind} · {len(WEAPONS)} armas')
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
