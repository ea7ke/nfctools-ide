#!/usr/bin/env python3
"""
MCT-IDE — Interfaz gráfica para las herramientas MIFARE Classic en Debian/Kali.

Envuelve nfc-list, mfoc, mfcuk y nfc-mfclassic con una interfaz de pestañas:
  - Lector:   detecta lector/tarjeta.
  - Leer:     lanza mfoc/mfcuk/nfc-mfclassic con opciones seleccionables.
  - Claves:   gestiona diccionarios de claves.
  - Tarjetas: organiza las tarjetas trabajadas por UID (base de datos local).
  - UID:      cambia el UID en tarjetas "magic" (detección + forzado).

Requiere: python3-pyqt5, libnfc-bin, mfoc, mfcuk (ver install.sh).
"""
import os
import shutil
import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QMessageBox, QWidget, QVBoxLayout, QLabel
)

from backend.carddb import CardDB
from backend.reader import CardInfo

from gui.reader_tab import ReaderTab
from gui.read_tab import ReadTab
from gui.keys_tab import KeysTab
from gui.cards_tab import CardsTab
from gui.uid_tab import UidTab

APP_NAME = "MCT-IDE"
DB_PATH = os.path.expanduser("~/.local/share/mct-ide/cards.db")

REQUIRED_BINARIES = ["nfc-list", "mfoc", "mfcuk", "nfc-mfclassic"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 700)

        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.card_db = CardDB(DB_PATH)
        self.active_card: CardInfo = None

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.reader_tab = ReaderTab(self)
        self.read_tab = ReadTab(self)
        self.keys_tab = KeysTab(self)
        self.cards_tab = CardsTab(self)
        self.uid_tab = UidTab(self)

        self.tabs.addTab(self.reader_tab, "Lector")
        self.tabs.addTab(self.read_tab, "Leer / Volcar")
        self.tabs.addTab(self.keys_tab, "Claves")
        self.tabs.addTab(self.cards_tab, "Tarjetas")
        self.tabs.addTab(self.uid_tab, "Editor de UID")

        self.status_label = QLabel("Ninguna tarjeta activa")
        self.statusBar().addPermanentWidget(self.status_label)

        self._check_dependencies()

    def set_active_card(self, card: CardInfo):
        self.active_card = card
        self.status_label.setText(f"Tarjeta activa: UID {card.uid}  ({card.guessed_type})")

    def _check_dependencies(self):
        missing = [b for b in REQUIRED_BINARIES if shutil.which(b) is None]
        if missing:
            QMessageBox.warning(
                self, "Faltan dependencias",
                "No se encuentran en el PATH estos binarios necesarios:\n\n"
                + "\n".join(f"  - {b}" for b in missing)
                + "\n\nInstálalos con install.sh o:\n"
                  "  sudo apt install libnfc-bin mfoc mfcuk"
            )

    def closeEvent(self, event):
        self.card_db.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
