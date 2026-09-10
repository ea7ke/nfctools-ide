"""
gui/process_runner.py
-----------------------
Envoltorio fino sobre QProcess para lanzar los binarios CLI (nfc-list,
mfoc, mfcuk, nfc-mfclassic) sin bloquear la interfaz, mostrando su
salida en vivo y notificando cuándo termina.
"""
from PyQt5.QtCore import QProcess, QObject, pyqtSignal


class ProcessRunner(QObject):
    line_ready = pyqtSignal(str)     # una línea de stdout/stderr
    finished = pyqtSignal(int, str)  # código de salida, salida completa acumulada

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_ready_read)
        self.process.finished.connect(self._on_finished)
        self._buffer = ""

    def run(self, cmd: list):
        if not cmd:
            return
        self._buffer = ""
        program, args = cmd[0], cmd[1:]
        self.process.start(program, args)

    def is_running(self) -> bool:
        return self.process.state() != QProcess.NotRunning

    def stop(self):
        if self.is_running():
            self.process.kill()

    def _on_ready_read(self):
        chunk = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        self._buffer += chunk
        for line in chunk.splitlines():
            self.line_ready.emit(line)

    def _on_finished(self, exit_code, _exit_status):
        self.finished.emit(exit_code, self._buffer)
