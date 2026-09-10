"""
backend/dumpio.py
-------------------
Carga/guarda ficheros de volcado (.mfd / .dump, binarios de 320 o 1024/4096
bytes según 1K/4K) y los presenta como bloques de 16 bytes en hexadecimal
para el visor/editor de la GUI.
"""
from dataclasses import dataclass
from typing import List
import os

BLOCK_SIZE = 16
SIZE_1K = 1024   # 64 bloques
SIZE_4K = 4096   # 256 bloques


@dataclass
class DumpBlock:
    index: int
    sector: int
    is_trailer: bool
    data: bytes

    @property
    def hex(self) -> str:
        return self.data.hex().upper()


def load_dump(path: str) -> bytes:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) not in (SIZE_1K, SIZE_4K):
        # No abortamos: puede ser un volcado parcial o de otra variante.
        pass
    return data


def save_dump(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


def blocks_from_dump(data: bytes) -> List[DumpBlock]:
    blocks = []
    n_blocks = len(data) // BLOCK_SIZE
    for i in range(n_blocks):
        chunk = data[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE]
        sector, is_trailer = _sector_for_block(i, n_blocks)
        blocks.append(DumpBlock(index=i, sector=sector, is_trailer=is_trailer, data=chunk))
    return blocks


def _sector_for_block(block_index: int, total_blocks: int) -> (int, bool):
    """
    Sectores 0-31: 4 bloques cada uno (bloques 0-127).
    Sectores 32-39 (solo 4K): 16 bloques cada uno (bloques 128-255).
    """
    if block_index < 128:
        sector = block_index // 4
        is_trailer = (block_index % 4) == 3
    else:
        offset = block_index - 128
        sector = 32 + offset // 16
        is_trailer = (offset % 16) == 15
    return sector, is_trailer


def default_dump_name(uid_hex: str, suffix: str = "") -> str:
    clean_uid = uid_hex.replace(" ", "").replace(":", "").upper()
    base = f"{clean_uid}{('_' + suffix) if suffix else ''}.mfd"
    return base
