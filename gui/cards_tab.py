"""
gui/cards_tab.py
-------------------
Pestaña 'Tarjetas': organiza las tarjetas trabajadas por UID, con nombre,
tipo, ruta de volcado y de claves, y notas. Permite abrir el volcado en el
visor, marcar una fila como tarjeta activa (para las pestañas Leer/UID),
renombrar/anotar y borrar.
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt

from backend.reader import CardInfo
from gui.dump_viewer import DumpViewerDialog

COLUMNS = ["UID", "Nombre", "Tipo", "Volcado", "Claves", "Notas", "Actualizado"]


class CardsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por UID o nombre…")
        self.search_edit.textChanged.connect(self.refresh)
        search_row.addWidget(self.search_edit)
        refresh_btn = QPushButton("Refrescar")
        refresh_btn.clicked.connect(self.refresh)
        search_row.addWidget(refresh_btn)
        layout.addLayout(search_row)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        activate_btn = QPushButton("Usar como tarjeta activa")
        activate_btn.clicked.connect(self.activate_selected)
        view_btn = QPushButton("Ver volcado")
        view_btn.clicked.connect(self.view_dump)
        rename_btn = QPushButton("Renombrar / anotar…")
        rename_btn.clicked.connect(self.rename_selected)
        delete_btn = QPushButton("Eliminar de la base de datos")
        delete_btn.clicked.connect(self.delete_selected)
        btn_row.addWidget(activate_btn)
        btn_row.addWidget(view_btn)
        btn_row.addWidget(rename_btn)
        btn_row.addWidget(delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        search = self.search_edit.text().strip()
        records = self.main_window.card_db.list_cards(search=search)
        self.table.setRowCount(len(records))
        self._records = records
        for row, rec in enumerate(records):
            values = [rec.uid, rec.name, rec.card_type, rec.dump_path,
                      rec.keys_path, rec.notes, rec.updated_at]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val or "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

    def _selected_record(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_records", [])):
            return None
        return self._records[row]

    def activate_selected(self):
        rec = self._selected_record()
        if not rec:
            QMessageBox.information(self, "Selecciona una fila", "Elige primero una tarjeta de la tabla.")
            return
        card = CardInfo(uid=rec.uid, guessed_type=rec.card_type)
        self.main_window.set_active_card(card)
        QMessageBox.information(self, "Tarjeta activa", f"UID {rec.uid} marcada como tarjeta activa.")

    def view_dump(self):
        rec = self._selected_record()
        if not rec:
            QMessageBox.information(self, "Selecciona una fila", "Elige primero una tarjeta de la tabla.")
            return
        if not rec.dump_path or not os.path.exists(rec.dump_path):
            QMessageBox.warning(self, "Sin volcado", "Esta tarjeta no tiene un volcado guardado (o el fichero ya no existe).")
            return
        dlg = DumpViewerDialog(self, rec.dump_path, editable_block0=False)
        dlg.exec_()

    def rename_selected(self):
        rec = self._selected_record()
        if not rec:
            QMessageBox.information(self, "Selecciona una fila", "Elige primero una tarjeta de la tabla.")
            return
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Nombre de la tarjeta", "Nombre:", text=rec.name)
        if not ok:
            return
        notes, ok2 = QInputDialog.getText(self, "Notas", "Notas:", text=rec.notes)
        if not ok2:
            notes = rec.notes
        self.main_window.card_db.upsert_card(uid=rec.uid, name=name, notes=notes)
        self.refresh()

    def delete_selected(self):
        rec = self._selected_record()
        if not rec:
            QMessageBox.information(self, "Selecciona una fila", "Elige primero una tarjeta de la tabla.")
            return
        confirm = QMessageBox.question(self, "Confirmar",
                                        f"¿Eliminar la tarjeta {rec.uid} de la base de datos?\n"
                                        "(esto no borra el fichero de volcado del disco)")
        if confirm == QMessageBox.Yes:
            self.main_window.card_db.delete_card(rec.uid)
            self.refresh()
