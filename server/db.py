"""Armazenamento das salas.

Com a variável DATABASE_URL (Render), usa PostgreSQL via psycopg.
Sem ela, usa um arquivo SQLite em data/ecos.db, para rodar no próprio PC.
"""
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.url = os.environ.get('DATABASE_URL', '').strip()
        self.kind = 'postgres' if self.url else 'sqlite'
        self._connect()
        self._schema()

    def _connect(self):
        if self.kind == 'postgres':
            import psycopg  # instalado pelo requirements.txt no Render
            self.conn = psycopg.connect(self.url, autocommit=True)
        else:
            (ROOT / 'data').mkdir(exist_ok=True)
            self.conn = sqlite3.connect(str(ROOT / 'data' / 'ecos.db'), check_same_thread=False)

    def _schema(self):
        if self.kind == 'postgres':
            self._exec('CREATE TABLE IF NOT EXISTS rooms (code TEXT PRIMARY KEY, data TEXT NOT NULL, updated DOUBLE PRECISION NOT NULL)')
            self._exec('CREATE TABLE IF NOT EXISTS rolls (id BIGSERIAL PRIMARY KEY, room TEXT NOT NULL, data TEXT NOT NULL, ts DOUBLE PRECISION NOT NULL)')
            self._exec('CREATE INDEX IF NOT EXISTS rolls_room ON rolls(room, id)')
        else:
            self._exec('CREATE TABLE IF NOT EXISTS rooms (code TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)')
            self._exec('CREATE TABLE IF NOT EXISTS rolls (id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT NOT NULL, data TEXT NOT NULL, ts REAL NOT NULL)')
            self._exec('CREATE INDEX IF NOT EXISTS rolls_room ON rolls(room, id)')

    def _q(self, sql):
        return sql.replace('?', '%s') if self.kind == 'postgres' else sql

    def _exec(self, sql, params=(), fetch=False):
        with self.lock:
            for attempt in (1, 2):
                try:
                    cur = self.conn.cursor()
                    cur.execute(self._q(sql), params)
                    rows = cur.fetchall() if fetch else None
                    if self.kind == 'sqlite':
                        self.conn.commit()
                    return rows
                except Exception:
                    if attempt == 2 or self.kind != 'postgres':
                        raise
                    self._connect()  # conexão caiu (o Render reinicia o banco às vezes)

    def save_room(self, code, data):
        payload = json.dumps(data, ensure_ascii=False)
        if self.kind == 'postgres':
            self._exec('INSERT INTO rooms (code, data, updated) VALUES (?, ?, ?) ON CONFLICT (code) DO UPDATE SET data = EXCLUDED.data, updated = EXCLUDED.updated', (code, payload, time.time()))
        else:
            self._exec('INSERT OR REPLACE INTO rooms (code, data, updated) VALUES (?, ?, ?)', (code, payload, time.time()))

    def load_room(self, code):
        rows = self._exec('SELECT data FROM rooms WHERE code = ?', (code,), fetch=True)
        return json.loads(rows[0][0]) if rows else None

    def add_roll(self, code, data):
        self._exec('INSERT INTO rolls (room, data, ts) VALUES (?, ?, ?)', (code, json.dumps(data, ensure_ascii=False), time.time()))

    def recent_rolls(self, code, limit=60):
        rows = self._exec('SELECT data FROM rolls WHERE room = ? ORDER BY id DESC LIMIT ?', (code, limit), fetch=True)
        return [json.loads(r[0]) for r in rows]
