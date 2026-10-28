"""Consola de mantenimiento de solo lectura sobre la conexion existente."""
import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QLineEdit, QPushButton, QCheckBox, QFileDialog, QMessageBox,
    QComboBox,
)

# Comandos sin actuacion: no se permiten ordenes de movimiento desde esta consola.
READ_ONLY_COMMANDS = {
    "sensor_status", "encoder_raw", "test_limits", "driver_status",
    "motor_status", "get_config",
}


class DiagnosticConsole(QWidget):
    def __init__(self, connection_manager, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.connection_manager = connection_manager
        self.setWindowTitle("Diagnostico - Pendulo invertido")
        self.resize(780, 480)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.entries = []

        root = QVBoxLayout(self)
        self.connection_label = QLabel()
        root.addWidget(self.connection_label)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(1500)
        root.addWidget(self.output)

        toolbar = QHBoxLayout()
        self.quick = QComboBox()
        self.quick.addItems(sorted(READ_ONLY_COMMANDS))
        quick_button = QPushButton("Consultar")
        quick_button.clicked.connect(self.send_quick)
        toolbar.addWidget(QLabel("Consulta rapida:"))
        toolbar.addWidget(self.quick, 1)
        toolbar.addWidget(quick_button)
        root.addLayout(toolbar)

        line = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText('{"type":"command","command":"encoder_raw"}')
        self.command_input.returnPressed.connect(self.send_manual)
        send_button = QPushButton("Enviar JSON")
        send_button.clicked.connect(self.send_manual)
        line.addWidget(self.command_input, 1)
        line.addWidget(send_button)
        root.addLayout(line)

        footer = QHBoxLayout()
        self.show_telemetry = QCheckBox("Mostrar telemetria (alto volumen)")
        clear_button = QPushButton("Limpiar")
        export_button = QPushButton("Exportar registro")
        clear_button.clicked.connect(self.clear_log)
        export_button.clicked.connect(self.export_log)
        footer.addWidget(self.show_telemetry)
        footer.addStretch(1)
        footer.addWidget(clear_button)
        footer.addWidget(export_button)
        root.addLayout(footer)

        self.connection_manager.connection_changed.connect(self.update_connection)
        self.update_connection(self.connection_manager.connected)

    def update_connection(self, connected):
        mode = "TCP" if self.connection_manager.current_mode == self.connection_manager.NETWORK else "Serial"
        self.connection_label.setText(
            f"Transporte: {mode} | Estado: {'Conectado' if connected else 'Desconectado'}"
        )

    def log(self, direction, payload):
        stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        else:
            body = str(payload)
        entry = f"[{stamp}] [{direction}] {body}"
        self.entries.append(entry)
        if len(self.entries) > 10000:
            del self.entries[:len(self.entries) - 10000]
        self.output.appendPlainText(entry)

    def receive(self, data):
        if not isinstance(data, dict):
            return
        if data.get("type") == "heartbeat":
            return
        if data.get("type") == "telemetry" and not self.show_telemetry.isChecked():
            return
        if self.isVisible():
            self.log("RX", data)

    def send_quick(self):
        self._send({"type": "command", "command": self.quick.currentText()})

    def send_manual(self):
        try:
            payload = json.loads(self.command_input.text())
        except json.JSONDecodeError as exc:
            QMessageBox.warning(self, "JSON invalido", str(exc))
            return
        self._send(payload)

    def _send(self, payload):
        if not isinstance(payload, dict) or payload.get("type") != "command" or payload.get("command") not in READ_ONLY_COMMANDS:
            QMessageBox.warning(
                self, "Comando no permitido",
                "Esta consola solo permite consultas de diagnostico."
            )
            return
        if not self.connection_manager.connected:
            QMessageBox.warning(self, "Sin conexion", "Conecta primero el ESP32.")
            return
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self.connection_manager.send(encoded)
        self.log("TX", payload)
        self.command_input.clear()

    def clear_log(self):
        self.entries.clear()
        self.output.clear()

    def export_log(self):
        destination, _ = QFileDialog.getSaveFileName(
            self, "Guardar diagnostico", "diagnostico_pendulo.txt", "Texto (*.txt)"
        )
        if destination:
            try:
                Path(destination).write_text("\n".join(self.entries) + "\n", encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "Error al guardar", str(exc))
