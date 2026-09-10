import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox, QTextEdit,
    QFileDialog, QMessageBox, QStackedWidget
)

from backend.mfoc_wrapper import MfocOptions, build_mfoc_cmd
from backend.mfcuk_wrapper import MfcukOptions, build_mfcuk_cmd
from backend.nfc_mfclassic_wrapper import ReadOptions, build_read_cmd
from backend.dumpio import default_dump_name
from gui.process_runner import ProcessRunner

METHOD_MFOC = "mfoc (nested/dictionary, requiere alguna clave conocida)"
METHOD_MFCUK = "mfcuk (darkside, sin claves conocidas, más lento)"
METHOD_NFC_MFCLASSIC = "nfc-mfclassic (lectura directa, claves ya conocidas)"


class ReadTab(QWidget):
    """Pestaña 'Leer / Volcar': lanza mfoc/mfcuk/nfc-mfclassic con opciones amigables."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = ProcessRunner(self)
        self.runner.line_ready.connect(self._append_log)
        self.runner.finished.connect(self._on_finished)
        self._build_ui()

    # ---------------------------------------------------------- UI ----
    def _build_ui(self):
        layout = QVBoxLayout(self)

        method_box = QGroupBox("Método")
        m_layout = QVBoxLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItems([METHOD_MFOC, METHOD_MFCUK, METHOD_NFC_MFCLASSIC])
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        m_layout.addWidget(self.method_combo)
        method_box.setLayout(m_layout)
        layout.addWidget(method_box)

        self.options_stack = QStackedWidget()
        self.options_stack.addWidget(self._build_mfoc_options())
        self.options_stack.addWidget(self._build_mfcuk_options())
        self.options_stack.addWidget(self._build_nfcmfclassic_options())
        layout.addWidget(self.options_stack)

        out_box = QGroupBox("Salida")
        out_form = QFormLayout()
        self.output_edit = QLineEdit()
        out_browse = QPushButton("Guardar como…")
        out_browse.clicked.connect(self._choose_output)
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_edit)
        out_row.addWidget(out_browse)
        out_form.addRow("Fichero de volcado (.mfd):", out_row)
        out_box.setLayout(out_form)
        layout.addWidget(out_box)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Ejecutar")
        self.run_btn.clicked.connect(self.run)
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.clicked.connect(self.runner.stop)
        self.stop_btn.setEnabled(False)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.stop_btn)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Salida del proceso:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def _build_mfoc_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.mfoc_only_keys = QLineEdit()
        b1 = QPushButton("…")
        b1.clicked.connect(lambda: self._browse_into(self.mfoc_only_keys))
        row1 = QHBoxLayout(); row1.addWidget(self.mfoc_only_keys); row1.addWidget(b1)
        form.addRow("Usar SOLO estas claves (-f, opcional):", row1)

        self.mfoc_extra_keys = QLineEdit()
        b2 = QPushButton("…")
        b2.clicked.connect(lambda: self._browse_into(self.mfoc_extra_keys))
        row2 = QHBoxLayout(); row2.addWidget(self.mfoc_extra_keys); row2.addWidget(b2)
        form.addRow("Diccionario adicional (-k, opcional):", row2)
        return w

    def _build_mfcuk_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.mfcuk_sector = QSpinBox()
        self.mfcuk_sector.setRange(0, 39)
        form.addRow("Sector objetivo:", self.mfcuk_sector)

        self.mfcuk_keytype = QComboBox()
        self.mfcuk_keytype.addItems(["A", "B"])
        form.addRow("Tipo de clave:", self.mfcuk_keytype)

        self.mfcuk_weak = QSpinBox()
        self.mfcuk_weak.setRange(0, 20)
        self.mfcuk_weak.setSpecialValueText("(desactivado)")
        form.addRow("Umbral 'weak card' (-w, opcional):", self.mfcuk_weak)
        return w

    def _build_nfcmfclassic_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.roc_keytype = QComboBox()
        self.roc_keytype.addItems(["a", "b"])
        form.addRow("Tipo de clave a usar:", self.roc_keytype)
        note = QLabel("Requiere que la tarjeta ya tenga claves conocidas\n"
                       "(usa primero mfoc/mfcuk, o carga un keyfile ya validado).")
        note.setWordWrap(True)
        form.addRow(note)
        return w

    # ------------------------------------------------------ helpers ----
    def _browse_into(self, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar fichero de claves")
        if path:
            line_edit.setText(path)

    def _choose_output(self):
        suggested = ""
        card = self.main_window.active_card
        if card and card.uid:
            suggested = default_dump_name(card.uid)
        path, _ = QFileDialog.getSaveFileName(self, "Guardar volcado como", suggested,
                                               "Volcado MIFARE (*.mfd)")
        if path:
            self.output_edit.setText(path)

    def _on_method_changed(self, index: int):
        self.options_stack.setCurrentIndex(index)

    # -------------------------------------------------------- acción ----
    def run(self):
        if not self.output_edit.text().strip():
            QMessageBox.warning(self, "Falta la salida", "Indica dónde guardar el volcado.")
            return

        idx = self.method_combo.currentIndex()
        if idx == 0:
            opts = MfocOptions(
                output_dump=self.output_edit.text().strip(),
                extra_keys_file=self.mfoc_extra_keys.text().strip() or None,
                only_keys_file=self.mfoc_only_keys.text().strip() or None,
            )
            cmd = build_mfoc_cmd(opts)
        elif idx == 1:
            weak = self.mfcuk_weak.value()
            opts = MfcukOptions(
                sector=self.mfcuk_sector.value(),
                key_type=self.mfcuk_keytype.currentText(),
                weak_threshold=weak if weak > 0 else None,
            )
            cmd = build_mfcuk_cmd(opts)
        else:
            opts = ReadOptions(
                dump_path=self.output_edit.text().strip(),
                key_type=self.roc_keytype.currentText(),
            )
            cmd = build_read_cmd(opts)

        self.log.clear()
        self.log.append("$ " + " ".join(cmd))
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.runner.run(cmd)

    def _append_log(self, line: str):
        self.log.append(line)

    def _on_finished(self, exit_code, _full_output):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log.append(f"\n[proceso terminado, código {exit_code}]")

        out_path = self.output_edit.text().strip()
        if exit_code == 0 and out_path and os.path.exists(out_path):
            card = self.main_window.active_card
            if card and card.uid:
                self.main_window.card_db.upsert_card(uid=card.uid, dump_path=out_path)
                self.main_window.cards_tab.refresh()
            QMessageBox.information(self, "Listo", f"Volcado guardado en:\n{out_path}")
