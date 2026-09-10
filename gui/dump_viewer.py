"""
gui/dump_viewer.py
--------------------
Diálogo que muestra un volcado .mfd como tabla de bloques de 16 bytes en
hexadecimal, marcando sectores y bloques trailer (los que contienen las
claves A/B y los bits de acceso). Permite editar el bloque 0 (UID) a mano
como paso previo a escribirlo con nfc-mfclassic.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt

from backend.dumpio import load_dump, save_dump, blocks_from_dump


class DumpViewerDialog(QDialog):
    def __init__(self, parent, dump_path: str, editable_block0: bool = False):
        super().__init__(parent)
        self.setWindowTitle(f"Volcado: {dump_path}")
        self.resize(720, 560)
        self.dump_path = dump_path
        self.editable_block0 = editable_block0
        self.data = load_dump(dump_path)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(f"Tamaño: {len(self.data)} bytes  |  "
                       f"Bloques: {len(self.data) // 16}  |  "
                       + ("Bloque 0 EDITABLE (doble clic para cambiar hex)"
                          if self.editable_block0 else "Solo lectura"))
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Bloque", "Sector", "Tipo", "Datos (hex)"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        save_as_btn = QPushButton("Guardar copia como…")
        save_as_btn.clicked.connect(self.save_as)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_as_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _populate(self):
        self.table.blockSignals(True)
        blocks = blocks_from_dump(self.data)
        self.table.setRowCount(len(blocks))
        for row, b in enumerate(blocks):
            tipo = "Trailer (claves)" if b.is_trailer else ("Manufacturer/UID" if b.index == 0 else "Datos")
            self.table.setItem(row, 0, self._ro_item(str(b.index)))
            self.table.setItem(row, 1, self._ro_item(str(b.sector)))
            self.table.setItem(row, 2, self._ro_item(tipo))

            hex_item = QTableWidgetItem(b.hex)
            editable_here = self.editable_block0 and b.index == 0
            if not editable_here:
                hex_item.setFlags(hex_item.flags() & ~Qt.ItemIsEditable)
            else:
                hex_item.setBackground(Qt.yellow)
            self.table.setItem(row, 3, hex_item)
        self.table.blockSignals(False)

    @staticmethod
    def _ro_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _on_item_changed(self, item: QTableWidgetItem):
        if item.column() != 3:
            return
        row = item.row()
        if row != 0 or not self.editable_block0:
            return
        text = item.text().replace(" ", "").strip().upper()
        if len(text) != 32 or any(c not in "0123456789ABCDEF" for c in text):
            QMessageBox.warning(self, "Hex inválido",
                                 "El bloque 0 debe ser exactamente 32 caracteres "
                                 "hexadecimales (16 bytes).")
            self.table.blockSignals(True)
            item.setText(self.data[:16].hex().upper())
            self.table.blockSignals(False)
            return
        new_block0 = bytes.fromhex(text)
        self.data = new_block0 + self.data[16:]

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar volcado como", self.dump_path,
                                               "Volcado MIFARE (*.mfd)")
        if not path:
            return
        try:
            save_dump(path, self.data)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
            return
        QMessageBox.information(self, "Guardado", f"Copia guardada en:\n{path}")
