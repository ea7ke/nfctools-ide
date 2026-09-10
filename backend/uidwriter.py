"""
backend/uidwriter.py
----------------------
Edición del bloque 0 (UID + BCC + SAK + ATQA + fabricante) y utilidades
para el flujo de "detección + forzar intento" de escritura de UID.

IMPORTANTE (léelo antes de usar el módulo en la GUI):
  - Una tarjeta MIFARE Classic ORIGINAL tiene el bloque 0 escrito de
    fábrica y de solo lectura: no hay forma de cambiarle el UID.
  - Solo los clones "magic" (Gen1a con comandos de puerta trasera 0x40/0x43,
    o Gen2 "CUID" que permiten reescritura directa) aceptan un nuevo UID.
  - Este módulo NO implementa un detector 100% fiable por software puro
    (eso requeriría enviar APDUs raw de puerta trasera, fuera del alcance
    de nfc-mfclassic). En su lugar ofrece:
      1) `build_self_write_test()`: una prueba NO destructiva que reescribe
         el bloque 0 con el MISMO UID que ya tiene la tarjeta. Si falla,
         casi seguro NO es una tarjeta "magic" (o el lector no soporta
         bypass de auth). Si tiene éxito, es compatible con reescritura
         de bloque 0.
      2) Un botón de "forzar intento" en la GUI que permite saltarse esta
         comprobación e intentar escribir un UID nuevo directamente,
         para quien ya sabe que su tarjeta es "magic" (p.ej. Gen1a
         comprado explícitamente para clonar sus propias tarjetas).
"""
from dataclasses import dataclass
from typing import List, Tuple
from .nfc_mfclassic_wrapper import WriteOptions, build_write_cmd


def compute_bcc(uid_bytes: List[int]) -> int:
    """BCC (Block Check Character) = XOR de los 4 bytes de UID (UID de 4 bytes)."""
    if len(uid_bytes) != 4:
        raise ValueError("Este cálculo de BCC asume UID de 4 bytes (el caso común).")
    bcc = 0
    for b in uid_bytes:
        bcc ^= b
    return bcc


def parse_uid_hex(uid_str: str) -> List[int]:
    """'04 A2 B1 C3' o '04A2B1C3' -> [0x04, 0xA2, 0xB1, 0xC3]"""
    clean = uid_str.replace(" ", "").replace(":", "").replace("-", "")
    if len(clean) not in (8, 14):  # 4 bytes u 7 bytes (UID largo, menos común en Classic)
        raise ValueError(f"UID con longitud inesperada: {uid_str!r}")
    return [int(clean[i:i + 2], 16) for i in range(0, len(clean), 2)]


def build_new_block0(uid_bytes: List[int], sak: int, atqa: Tuple[int, int],
                      manufacturer_data: bytes = None) -> bytes:
    """
    Construye los 16 bytes del bloque 0:
    [UID(4)] [BCC(1)] [SAK(1)] [ATQA(2)] [datos de fabricante(8)]
    """
    if len(uid_bytes) != 4:
        raise ValueError("Solo se soporta edición de UID de 4 bytes en este flujo.")
    bcc = compute_bcc(uid_bytes)
    manuf = manufacturer_data if manufacturer_data else bytes(8)
    if len(manuf) != 8:
        raise ValueError("manufacturer_data debe tener 8 bytes.")
    block0 = bytes(uid_bytes) + bytes([bcc, sak]) + bytes(atqa) + manuf
    if len(block0) != 16:
        raise ValueError("El bloque 0 resultante no tiene 16 bytes, revisa los datos.")
    return block0


def patch_dump_block0(dump_bytes: bytes, new_block0: bytes) -> bytes:
    """Sustituye los primeros 16 bytes de un volcado .mfd por el nuevo bloque 0."""
    if len(dump_bytes) < 16:
        raise ValueError("El volcado es demasiado pequeño para contener un bloque 0.")
    if len(new_block0) != 16:
        raise ValueError("new_block0 debe tener exactamente 16 bytes.")
    return new_block0 + dump_bytes[16:]


@dataclass
class UidWriteResult:
    attempted: bool
    forced: bool
    cmd: List[str]


def build_self_write_test(dump_path: str, key_type: str = "a") -> List[str]:
    """
    Comando para el test no destructivo: reescribe el bloque 0 con los
    mismos datos que ya tiene la tarjeta (dump_path debe ser un volcado
    recién leído de ESA tarjeta, sin modificar). Si nfc-mfclassic devuelve
    error de escritura de bloque 0, se asume tarjeta no-magic.
    """
    opts = WriteOptions(dump_path=dump_path, key_type=key_type, write_uid_block0=True)
    return build_write_cmd(opts)


def build_uid_write_cmd(dump_path_with_new_uid: str, key_type: str = "a",
                         forced: bool = False) -> UidWriteResult:
    """
    Comando real para grabar un UID nuevo. `dump_path_with_new_uid` debe ser
    un volcado cuyo bloque 0 ya se parcheó con `patch_dump_block0`.
    `forced=True` indica que el usuario se saltó la detección previa.
    """
    opts = WriteOptions(dump_path=dump_path_with_new_uid, key_type=key_type,
                         write_uid_block0=True)
    cmd = build_write_cmd(opts)
    return UidWriteResult(attempted=True, forced=forced, cmd=cmd)
