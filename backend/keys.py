"""
backend/keys.py
------------------
Carga, valida, fusiona y guarda ficheros de diccionario de claves
(formato estándar: una clave hexadecimal de 12 caracteres por línea,
p.ej. "FFFFFFFFFFFF").
"""
from typing import List, Set
import re

_KEY_RE = re.compile(r"^[0-9a-fA-F]{12}$")

DEFAULT_KEYS = [
    "FFFFFFFFFFFF",
    "000000000000",
    "A0A1A2A3A4A5",
    "D3F7D3F7D3F7",
    "B0B1B2B3B4B5",
]


def load_keys(path: str) -> List[str]:
    keys = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            k = line.strip()
            if not k or k.startswith("#"):
                continue
            if _KEY_RE.match(k):
                keys.append(k.upper())
    return keys


def save_keys(path: str, keys: List[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for k in keys:
            f.write(k.upper() + "\n")


def merge_keys(*key_lists: List[str]) -> List[str]:
    seen: Set[str] = set()
    merged: List[str] = []
    for lst in key_lists:
        for k in lst:
            ku = k.upper()
            if _KEY_RE.match(ku) and ku not in seen:
                seen.add(ku)
                merged.append(ku)
    return merged


def is_valid_key(key: str) -> bool:
    return bool(_KEY_RE.match(key.strip()))
