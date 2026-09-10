"""
backend/mfoc_wrapper.py
------------------------
Construye la línea de comandos de `mfoc` (ataque nested/dictionary) a partir
de opciones seleccionadas en la GUI, y parsea el progreso/las claves que va
imprimiendo por stdout.

mfoc no soporta rango de sectores por CLI en la mayoría de builds; ataca
todos los sectores usando la(s) clave(s) conocida(s) como semilla del
ataque nested. Si tu build de mfoc soporta flags distintos, ajusta
MFOC_BIN y las opciones aquí.
"""
from dataclasses import dataclass, field
from typing import List, Optional
import re

MFOC_BIN = "mfoc"


@dataclass
class MfocOptions:
    output_dump: str                       # ruta del .mfd de salida (-O)
    extra_keys_file: Optional[str] = None  # diccionario adicional (-k)
    only_keys_file: Optional[str] = None   # usar SOLO estas claves (-f), si el build lo soporta
    verbosity: int = 1                     # -v (algunas builds no lo soportan)


def build_mfoc_cmd(opts: MfocOptions) -> List[str]:
    cmd = [MFOC_BIN]
    if opts.only_keys_file:
        cmd += ["-f", opts.only_keys_file]
    if opts.extra_keys_file:
        cmd += ["-k", opts.extra_keys_file]
    cmd += ["-O", opts.output_dump]
    return cmd


# --- Parseo de progreso ------------------------------------------------

_KEY_LINE_RE = re.compile(
    r"Sector\s+(?P<sector>\d+)\s*[-:]?.*key\s*(?P<type>[AB])\s*[:=]?\s*(?P<key>[0-9a-fA-F]{12})",
    re.IGNORECASE,
)


@dataclass
class RecoveredKey:
    sector: int
    key_type: str  # "A" o "B"
    key_hex: str


def parse_mfoc_line(line: str) -> Optional[RecoveredKey]:
    """Intenta extraer una clave recuperada de una línea de salida de mfoc."""
    m = _KEY_LINE_RE.search(line)
    if not m:
        return None
    return RecoveredKey(
        sector=int(m.group("sector")),
        key_type=m.group("type").upper(),
        key_hex=m.group("key").lower(),
    )


def is_success_line(line: str) -> bool:
    low = line.lower()
    return "wrote" in low and "dump" in low or "successfully" in low
