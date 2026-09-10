"""
backend/mfcuk_wrapper.py
-------------------------
Construye la línea de comandos de `mfcuk` (ataque darkside, útil cuando no
se tiene ninguna clave conocida) y parsea la clave recuperada.
"""
from dataclasses import dataclass
from typing import List, Optional
import re

MFCUK_BIN = "mfcuk"


@dataclass
class MfcukOptions:
    sector: int = 0
    key_type: str = "A"     # "A" o "B"
    verbosity: int = 2      # -v
    weak_threshold: Optional[int] = None  # -w N, para "weak cards"


def build_mfcuk_cmd(opts: MfcukOptions) -> List[str]:
    cmd = [
        MFCUK_BIN,
        "-C",
        "-R", f"{opts.sector}:{opts.key_type.upper()}",
        "-v", str(opts.verbosity),
    ]
    if opts.weak_threshold is not None:
        cmd += ["-w", str(opts.weak_threshold)]
    return cmd


_RECOVERED_RE = re.compile(r"key\s*[:=]?\s*(?P<key>[0-9a-fA-F]{12})", re.IGNORECASE)


def parse_mfcuk_recovered_key(text: str) -> Optional[str]:
    """Busca en toda la salida (o línea a línea) una clave de 6 bytes recuperada."""
    m = _RECOVERED_RE.search(text)
    if m:
        return m.group("key").lower()
    return None
