"""
backend/carddb.py
--------------------
Base de datos local (SQLite) para organizar tarjetas por UID: nombre,
tipo, ruta del volcado, ruta de claves encontradas, notas y fechas.
"""
import sqlite3
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    name TEXT,
    card_type TEXT,
    dump_path TEXT,
    keys_path TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@dataclass
class CardRecord:
    id: Optional[int]
    uid: str
    name: str
    card_type: str
    dump_path: str
    keys_path: str
    notes: str
    created_at: str
    updated_at: str


class CardDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def upsert_card(self, uid: str, name: str = "", card_type: str = "",
                     dump_path: str = "", keys_path: str = "", notes: str = "") -> None:
        now = datetime.utcnow().isoformat()
        existing = self.get_card(uid)
        if existing:
            self.conn.execute(
                """UPDATE cards SET name=?, card_type=?, dump_path=?, keys_path=?,
                   notes=?, updated_at=? WHERE uid=?""",
                (name or existing.name, card_type or existing.card_type,
                 dump_path or existing.dump_path, keys_path or existing.keys_path,
                 notes or existing.notes, now, uid),
            )
        else:
            self.conn.execute(
                """INSERT INTO cards (uid, name, card_type, dump_path, keys_path,
                   notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)""",
                (uid, name, card_type, dump_path, keys_path, notes, now, now),
            )
        self.conn.commit()

    def get_card(self, uid: str) -> Optional[CardRecord]:
        cur = self.conn.execute("SELECT * FROM cards WHERE uid=?", (uid,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def list_cards(self, search: str = "") -> List[CardRecord]:
        if search:
            like = f"%{search}%"
            cur = self.conn.execute(
                """SELECT * FROM cards WHERE uid LIKE ? OR name LIKE ?
                   ORDER BY updated_at DESC""",
                (like, like),
            )
        else:
            cur = self.conn.execute("SELECT * FROM cards ORDER BY updated_at DESC")
        return [self._row_to_record(r) for r in cur.fetchall()]

    def delete_card(self, uid: str) -> None:
        self.conn.execute("DELETE FROM cards WHERE uid=?", (uid,))
        self.conn.commit()

    @staticmethod
    def _row_to_record(row) -> CardRecord:
        return CardRecord(
            id=row[0], uid=row[1], name=row[2] or "", card_type=row[3] or "",
            dump_path=row[4] or "", keys_path=row[5] or "", notes=row[6] or "",
            created_at=row[7], updated_at=row[8],
        )
