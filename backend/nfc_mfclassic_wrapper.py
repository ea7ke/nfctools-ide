"""
backend/nfc_mfclassic_wrapper.py
----------------------------------
Envuelve `nfc-mfclassic`, usado para:
  - Leer una tarjeta con claves ya conocidas (más rápido que mfoc/mfcuk).
  - Escribir un volcado a una tarjeta.
  - Escribir el UID (bloque 0) en tarjetas "magic" que lo permiten.

Sintaxis real de nfc-mfclassic (libnfc):
    nfc-mfclassic R a|b <dump_file> [device]   -> leer
    nfc-mfclassic W a|b <dump_file> [device] [u]  -> escribir
        el flag final 'u' = también intenta escribir el bloque 0
        (UID/BCC/SAK/ATQA). Solo funciona en tarjetas "magic"
        (Gen1a / CUID) que aceptan reescritura de bloque 0.
"""
from dataclasses import dataclass
from typing import List, Optional

NFC_MFCLASSIC_BIN = "nfc-mfclassic"


@dataclass
class ReadOptions:
    dump_path: str
    key_type: str = "a"   # "a" o "b"


@dataclass
class WriteOptions:
    dump_path: str
    key_type: str = "a"
    write_uid_block0: bool = False  # requiere tarjeta "magic"


def build_read_cmd(opts: ReadOptions) -> List[str]:
    return [NFC_MFCLASSIC_BIN, "R", opts.key_type.lower(), opts.dump_path]


def build_write_cmd(opts: WriteOptions) -> List[str]:
    cmd = [NFC_MFCLASSIC_BIN, "W", opts.key_type.lower(), opts.dump_path]
    if opts.write_uid_block0:
        cmd.append("u")
    return cmd


def looks_like_magic_card_error(output: str) -> bool:
    """
    Heurística: si nfc-mfclassic falla al escribir el bloque 0 en una
    tarjeta normal, suele imprimir avisos de tipo 'Unable to write block 0'
    o similar. Se usa para el botón "detección automática" antes de
    habilitar el editor de UID.
    """
    low = output.lower()
    triggers = [
        "unable to write block 0",
        "failed to write block 0",
        "write block failed",
        "cannot write block 0",
    ]
    return any(t in low for t in triggers)
