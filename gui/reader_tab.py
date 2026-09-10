from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QGroupBox, QFormLayout, QLineEdit, QMessageBox
)
from backend.reader import build_nfc_list_cmd, parse_nfc_list_output, CardInfo
from gui.process_runner import ProcessRunner


class ReaderTab(QWidget):
    """Pestaña 'Lector': detecta el lector NFC y la tarjeta presente."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_card: CardInfo = None
        self.runner = ProcessRunner(self)
        self.runner.line_ready.connect(self._append_log)
        self.runner.finished.connect(self._on_finished)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self.detect_btn = QPushButton("Detectar lector / tarjeta")
        self.detect_btn.clicked.connect(self.detect)
        btn_row.addWidget(self.detect_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        info_box = QGroupBox("Tarjeta detectada")
        form = QFormLayout()
        self.uid_edit = QLineEdit()
        self.uid_edit.setReadOnly(True)
        self.atqa_edit = QLineEdit()
        self.atqa_edit.setReadOnly(True)
        self.sak_edit = QLineEdit()
        self.sak_edit.setReadOnly(True)
        self.type_edit = QLineEdit()
        self.type_edit.setReadOnly(True)
        form.addRow("UID:", self.uid_edit)
        form.addRow("ATQA:", self.atqa_edit)
        form.addRow("SAK:", self.sak_edit)
        form.addRow("Tipo estimado:", self.type_edit)
        info_box.setLayout(form)
        layout.addWidget(info_box)

        self.save_btn = QPushButton("Guardar tarjeta en base de datos")
        self.save_btn.clicked.connect(self.save_to_db)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)

        layout.addWidget(QLabel("Salida de nfc-list:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def detect(self):
        self.log.clear()
        self.detect_btn.setEnabled(False)
        self.runner.run(build_nfc_list_cmd())

    def _append_log(self, line: str):
        self.log.append(line)

    def _on_finished(self, exit_code, full_output):
        self.detect_btn.setEnabled(True)
        card = parse_nfc_list_output(full_output)
        if not card or not card.uid:
            QMessageBox.warning(self, "Sin tarjeta",
                                 "No se detectó ninguna tarjeta. Comprueba el lector "
                                 "y que hay una tarjeta sobre la antena.")
            self.save_btn.setEnabled(False)
            return
        self.current_card = card
        self.uid_edit.setText(card.uid)
        self.atqa_edit.setText(card.atqa)
        self.sak_edit.setText(card.sak)
        self.type_edit.setText(card.guessed_type)
        self.save_btn.setEnabled(True)
        # Notifica al resto de la app (pestañas Leer/UID) de la tarjeta activa
        self.main_window.set_active_card(card)

    def save_to_db(self):
        if not self.current_card:
            return
        self.main_window.card_db.upsert_card(
            uid=self.current_card.uid,
            card_type=self.current_card.guessed_type,
        )
        self.main_window.cards_tab.refresh()
        QMessageBox.information(self, "Guardado", "Tarjeta guardada/actualizada en la base de datos.")
