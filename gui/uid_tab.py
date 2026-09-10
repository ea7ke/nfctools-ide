"""
gui/uid_tab.py
-----------------
Pestaña 'Editor de UID': permite cambiar el UID (bloque 0) de tarjetas
"magic" (Gen1a / CUID). Flujo:

  1. Elegir el volcado de origen (normalmente el último leído de la
     tarjeta que tienes en el lector ahora mismo).
  2. "Comprobar si es 'magic'": ejecuta un test NO destructivo que
     reescribe el bloque 0 con el MISMO UID que ya tenía. Si
     nfc-mfclassic acepta la escritura, es compatible; si falla,
     probablemente no lo es.
  3. Si es compatible (o si el usuario pulsa "Forzar intento" saltándose
     el paso 2), se introduce el nuevo UID, se recalcula el BCC
     automáticamente, se previsualiza el bloque 0 resultante y se
     escribe en la tarjeta.

IMPORTANTE: una MIFARE Classic original NUNCA aceptará esto porque su
bloque 0 es de solo lectura de fábrica. Esta pestaña solo tiene sentido
con clones "magic" comprados para pruebas/clonado de tarjetas propias.
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

from backend.dumpio import load_dump, save_dump
from backend.nfc_mfclassic_wrapper import looks_like_magic_card_error
from backend.uidwriter import (
    parse_uid_hex, build_new_block0, patch_dump_block0,
    build_self_write_test, build_uid_write_cmd,
)
from gui.process_runner import ProcessRunner


class UidTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = ProcessRunner(self)
        self.runner.line_ready.connect(self._append_log)
        self.runner.finished.connect(self._on_process_finished)
        self._pending_action = None  # "detect" o "write"
        self._patched_dump_path = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        warn = QLabel(
            "⚠️ Solo funciona en tarjetas 'magic' (clones Gen1a / CUID). "
            "Una MIFARE Classic original tiene el UID grabado de fábrica y "
            "esto fallará siempre, como es esperado."
        )
        warn.setWordWrap(True)
        layout.addWidget(warn)

        src_box = QGroupBox("Volcado de origen (leído de la tarjeta que quieres modificar)")
        src_form = QFormLayout()
        self.source_edit = QLineEdit()
        src_browse = QPushButton("…")
        src_browse.clicked.connect(self._browse_source)
        src_row = QHBoxLayout()
        src_row.addWidget(self.source_edit)
        src_row.addWidget(src_browse)
        src_form.addRow("Fichero .mfd:", src_row)

        self.key_type_combo = QComboBox()
        self.key_type_combo.addItems(["a", "b"])
        src_form.addRow("Tipo de clave a usar al escribir:", self.key_type_combo)
        src_box.setLayout(src_form)
        layout.addWidget(src_box)

        detect_row = QHBoxLayout()
        detect_btn = QPushButton("1) Comprobar si es 'magic' (test no destructivo)")
        detect_btn.clicked.connect(self.run_detection)
        detect_row.addWidget(detect_btn)
        self.detect_result_label = QLabel("Estado: sin comprobar")
        detect_row.addWidget(self.detect_result_label)
        detect_row.addStretch()
        layout.addLayout(detect_row)

        new_uid_box = QGroupBox("2) Nuevo UID")
        uid_form = QFormLayout()
        self.new_uid_edit = QLineEdit()
        self.new_uid_edit.setPlaceholderText("p.ej. 04A2B1C3 (4 bytes)")
        uid_form.addRow("Nuevo UID (hex):", self.new_uid_edit)

        self.preview_label = QLabel("Bloque 0 previsto: —")
        self.preview_label.setWordWrap(True)
        uid_form.addRow(self.preview_label)

        preview_btn = QPushButton("Previsualizar bloque 0")
        preview_btn.clicked.connect(self.preview_block0)
        uid_form.addRow(preview_btn)
        new_uid_box.setLayout(uid_form)
        layout.addWidget(new_uid_box)

        action_row = QHBoxLayout()
        self.write_btn = QPushButton("3) Escribir nuevo UID")
        self.write_btn.clicked.connect(lambda: self.write_uid(forced=False))
        self.write_btn.setEnabled(False)
        self.force_btn = QPushButton("Forzar intento (saltar comprobación)")
        self.force_btn.clicked.connect(lambda: self.write_uid(forced=True))
        action_row.addWidget(self.write_btn)
        action_row.addWidget(self.force_btn)
        layout.addLayout(action_row)

        layout.addWidget(QLabel("Salida del proceso:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    # ------------------------------------------------------------------
    def _browse_source(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar volcado de origen",
                                               filter="Volcado MIFARE (*.mfd)")
        if path:
            self.source_edit.setText(path)

    def _current_uid_bytes(self):
        card = self.main_window.active_card
        if card and card.uid:
            try:
                return parse_uid_hex(card.uid)
            except ValueError:
                return None
        return None

    def preview_block0(self):
        try:
            new_uid = parse_uid_hex(self.new_uid_edit.text().strip())
        except ValueError as e:
            QMessageBox.warning(self, "UID inválido", str(e))
            return
        if len(new_uid) != 4:
            QMessageBox.warning(self, "UID inválido",
                                 "Este editor solo soporta UID de 4 bytes (el caso habitual en Classic).")
            return

        source = self.source_edit.text().strip()
        sak, atqa = 0x08, (0x00, 0x04)  # valores típicos MIFARE Classic 1K por defecto
        if source and os.path.exists(source):
            try:
                data = load_dump(source)
                if len(data) >= 16:
                    sak = data[5]
                    atqa = (data[6], data[7]) if len(data) > 7 else atqa
            except OSError:
                pass

        block0 = build_new_block0(new_uid, sak, atqa)
        self.preview_label.setText(f"Bloque 0 previsto: {block0.hex().upper()}")
        self._preview_block0_bytes = block0
        self.write_btn.setEnabled(True)

    # ------------------------------------------------------------------
    def run_detection(self):
        source = self.source_edit.text().strip()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "Falta el volcado",
                                 "Selecciona primero el volcado leído de la tarjeta actual.")
            return
        self._pending_action = "detect"
        self.log.clear()
        self.detect_result_label.setText("Estado: comprobando…")
        cmd = build_self_write_test(source, key_type=self.key_type_combo.currentText())
        self.log.append("$ " + " ".join(cmd))
        self.log.append("(Reescribe el bloque 0 con el MISMO UID que ya tiene la tarjeta; "
                         "no debería cambiar nada visible si tiene éxito.)")
        self.runner.run(cmd)

    def write_uid(self, forced: bool = False):
        if not getattr(self, "_preview_block0_bytes", None):
            QMessageBox.warning(self, "Falta previsualizar",
                                 "Pulsa antes 'Previsualizar bloque 0'.")
            return
        source = self.source_edit.text().strip()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "Falta el volcado",
                                 "Selecciona primero el volcado leído de la tarjeta actual.")
            return

        if forced:
            confirm = QMessageBox.question(
                self, "Confirmar intento forzado",
                "Vas a intentar escribir el UID SIN haber confirmado que la tarjeta "
                "es 'magic'. Si no lo es, la operación simplemente fallará (no debería "
                "dañar una tarjeta normal, pero procede bajo tu responsabilidad).\n\n"
                "¿Continuar?"
            )
            if confirm != QMessageBox.Yes:
                return

        data = load_dump(source)
        patched = patch_dump_block0(data, self._preview_block0_bytes)
        patched_path = source + ".newuid.mfd"
        save_dump(patched_path, patched)
        self._patched_dump_path = patched_path

        self._pending_action = "write"
        self.log.clear()
        result = build_uid_write_cmd(patched_path, key_type=self.key_type_combo.currentText(), forced=forced)
        self.log.append("$ " + " ".join(result.cmd))
        self.runner.run(result.cmd)

    # ------------------------------------------------------------------
    def _append_log(self, line: str):
        self.log.append(line)

    def _on_process_finished(self, exit_code, full_output):
        if self._pending_action == "detect":
            if exit_code == 0 and not looks_like_magic_card_error(full_output):
                self.detect_result_label.setText("Estado: ✅ compatible (probable tarjeta 'magic')")
            else:
                self.detect_result_label.setText("Estado: ❌ no compatible (probable tarjeta original o error de lectura)")
        elif self._pending_action == "write":
            if exit_code == 0 and not looks_like_magic_card_error(full_output):
                QMessageBox.information(self, "Listo", "UID escrito correctamente (según el código de salida).")
                # refresca la tarjeta activa releyendo el lector desde la pestaña Lector
                if hasattr(self.main_window, "reader_tab"):
                    self.main_window.reader_tab.detect()
            else:
                QMessageBox.warning(self, "Fallo al escribir",
                                     "nfc-mfclassic no confirmó la escritura del bloque 0. "
                                     "Revisa el log: probablemente la tarjeta no admite "
                                     "reescritura de UID.")
        self._pending_action = None
