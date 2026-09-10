"""
gui/keys_tab.py
-----------------
Pestaña 'Claves': cargar uno o varios ficheros de diccionario, ver las
claves combinadas, añadir claves sueltas a mano, y guardar el resultado
como un único fichero listo para usar en -k / -f.
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QLineEdit, QFileDialog, QMessageBox, QGroupBox,
    QListWidgetItem
)

from backend.keys import load_keys, save_keys, merge_keys, is_valid_key, DEFAULT_KEYS


class KeysTab(QWidget):
    """Pestaña 'Claves': gestor de diccionarios de claves MIFARE."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.keys = []  # lista actual combinada (mayúsculas, sin duplicados)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        load_btn = QPushButton("Cargar fichero de claves…")
        load_btn.clicked.connect(self.load_file)
        defaults_btn = QPushButton("Añadir claves por defecto")
        defaults_btn.clicked.connect(self.add_defaults)
        clear_btn = QPushButton("Vaciar lista")
        clear_btn.clicked.connect(self.clear_keys)
        btn_row.addWidget(load_btn)
        btn_row.addWidget(defaults_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        add_box = QGroupBox("Añadir clave manual (12 dígitos hex)")
        add_row = QHBoxLayout()
        self.manual_key_edit = QLineEdit()
        self.manual_key_edit.setPlaceholderText("p.ej. FFFFFFFFFFFF")
        self.manual_key_edit.returnPressed.connect(self.add_manual_key)
        add_btn = QPushButton("Añadir")
        add_btn.clicked.connect(self.add_manual_key)
        add_row.addWidget(self.manual_key_edit)
        add_row.addWidget(add_btn)
        add_box.setLayout(add_row)
        layout.addWidget(add_box)

        layout.addWidget(QLabel("Claves cargadas:"))
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        remove_row = QHBoxLayout()
        remove_btn = QPushButton("Quitar clave seleccionada")
        remove_btn.clicked.connect(self.remove_selected)
        remove_row.addWidget(remove_btn)
        remove_row.addStretch()
        layout.addLayout(remove_row)

        save_row = QHBoxLayout()
        self.save_path_edit = QLineEdit()
        browse_btn = QPushButton("Guardar como…")
        browse_btn.clicked.connect(self.save_file)
        save_row.addWidget(self.save_path_edit)
        save_row.addWidget(browse_btn)
        layout.addLayout(save_row)

        self.count_label = QLabel("0 claves")
        layout.addWidget(self.count_label)

    # ------------------------------------------------------------------
    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Cargar fichero de claves")
        if not path:
            return
        try:
            new_keys = load_keys(path)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el fichero:\n{e}")
            return
        if not new_keys:
            QMessageBox.warning(self, "Sin claves válidas",
                                 "El fichero no contenía claves con formato válido "
                                 "(12 dígitos hexadecimales por línea).")
            return
        self.keys = merge_keys(self.keys, new_keys)
        self._refresh_list()

    def add_defaults(self):
        self.keys = merge_keys(self.keys, DEFAULT_KEYS)
        self._refresh_list()

    def add_manual_key(self):
        k = self.manual_key_edit.text().strip()
        if not is_valid_key(k):
            QMessageBox.warning(self, "Clave inválida",
                                 "La clave debe tener exactamente 12 dígitos hexadecimales.")
            return
        self.keys = merge_keys(self.keys, [k])
        self.manual_key_edit.clear()
        self._refresh_list()

    def remove_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        key = item.text()
        self.keys = [k for k in self.keys if k != key]
        self._refresh_list()

    def clear_keys(self):
        self.keys = []
        self._refresh_list()

    def save_file(self):
        if not self.keys:
            QMessageBox.warning(self, "Nada que guardar", "La lista de claves está vacía.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar diccionario de claves",
                                               "claves.dic", "Diccionario (*.dic *.txt)")
        if not path:
            return
        try:
            save_keys(path, self.keys)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
            return
        self.save_path_edit.setText(path)
        QMessageBox.information(self, "Guardado", f"Diccionario guardado en:\n{path}")

    # ------------------------------------------------------------------
    def _refresh_list(self):
        self.list_widget.clear()
        for k in self.keys:
            self.list_widget.addItem(QListWidgetItem(k))
        self.count_label.setText(f"{len(self.keys)} claves")
