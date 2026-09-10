"""
backend/reader.py
------------------
Construye el comando para detectar lector/tarjeta con `nfc-list` y parsea
su salida en una estructura simple.

No ejecuta nada aquí: devuelve el argv listo para pasar a QProcess (o a
subprocess si se usa fuera de la GUI), y funciones puras de parseo para
poder testear sin hardware.
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class CardInfo:
    uid: str = ""
    atqa: str = ""
    sak: str = ""
    tech: str = ""            # p.ej. "ISO14443A"
    guessed_type: str = ""    # "MIFARE Classic 1K", "4K", "Desconocido"
    raw_output: str = ""


def build_nfc_list_cmd() -> List[str]:
    """Comando para listar el lector y la tarjeta presente, en modo verboso."""
    return ["nfc-list", "-v"]


def guess_card_type(sak: str) -> str:
    """
    Deduce el tipo de tarjeta a partir del byte SAK (Select Acknowledge).
    Valores típicos para MIFARE:
      0x08 -> MIFARE Classic 1K
      0x18 -> MIFARE Classic 4K
      0x09 -> MIFARE Mini
      0x00 -> MIFARE Ultralight / NTAG
    """
    if not sak:
        return "Desconocido"
    s = sak.lower().replace("0x", "").strip()
    table = {
        "08": "MIFARE Classic 1K",
        "18": "MIFARE Classic 4K",
        "09": "MIFARE Mini (0.3K)",
        "00": "MIFARE Ultralight / NTAG (no Classic)",
        "28": "MIFARE Classic 1K (emulado / magic)",
        "38": "MIFARE Classic 4K (emulado / magic)",
    }
    return table.get(s, f"Desconocido (SAK=0x{s})")


def parse_nfc_list_output(text: str) -> Optional[CardInfo]:
    """
    Parsea la salida de `nfc-list -v`. Formato típico (libnfc):

    NFC device: pn532_uart:/dev/ttyUSB0 opened
    1 ISO14443A passive target(s) found:
        ISO/IEC 14443A (106 kbps) target:
            ATQA (SENS_RES): 00  04
            UID (NFCID1): 04  a2  b1  c3
            SAK (SEL_RES): 08
            ...

    Es tolerante a variaciones de formato entre versiones de libnfc.
    """
    if not text or "target(s) found" not in text:
        return None

    info = CardInfo(raw_output=text)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        low = line.lower()
        if low.startswith("uid"):
            info.uid = _extract_hex_after_colon(line)
        elif low.startswith("atqa"):
            info.atqa = _extract_hex_after_colon(line)
        elif low.startswith("sak"):
            info.sak = _extract_hex_after_colon(line).replace(" ", "")
        elif "iso/iec 14443a" in low or "iso14443a" in low:
            info.tech = "ISO14443A"

    info.guessed_type = guess_card_type(info.sak)
    return info


def _extract_hex_after_colon(line: str) -> str:
    if ":" not in line:
        return ""
    value = line.split(":", 1)[1].strip()
    # normaliza separadores dobles de espacio a uno solo
    return " ".join(value.split())
