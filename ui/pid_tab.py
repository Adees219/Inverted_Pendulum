"""
Pestaña de control PID.

Define la clase PIDTab, encargada de:
    - Permitir seleccionar el punto de equilibrio del péndulo (arriba/abajo).
    - Configurar y validar las ganancias del controlador PID (Kp, Ki, Kd).
    - Mostrar el estado actual del sistema de control (modo, estado, frecuencia).
    - Graficar en tiempo real el ángulo y la señal de control (simulados por ahora).
    - Enviar la configuración PID al microcontrolador a través del ConnectionManager.
"""

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox
)

from ui.utils.widget_style import *  # Funciones auxiliares de estilo (dimensiones, colores, fuentes de los widgets)

from ui.constants.ui_constants import (  # Colores y textos estándar para los indicadores de estado
    STATUS_GREEN,
    STATUS_RED,
    STATUS_YELLOW,
    STATUS_ACTIVE,
    STATUS_INACTIVE,
    STATUS_WAITING
)

from PySide6.QtGui import (  # Validador para restringir la entrada a números decimales dentro de un rango
    QDoubleValidator
)

from models.pid_model import PIDModel  # Modelo que almacena y serializa las ganancias/modo del controlador PID

from plots.pid_plots import PIDPlots  # Widget de gráficas para visualizar ángulo y señal de control en tiempo real

from PySide6.QtCore import QTimer  # Temporizador usado para simular/actualizar las gráficas periódicamente
import json
import math  # Funciones matemáticas (usadas aquí para generar la señal simulada)


class PIDTab(QWidget):
    """
    Pestaña de control PID.

    Agrupa los controles para configurar el punto de equilibrio y las
    ganancias del PID, muestra el estado del sistema de control y despliega
    las gráficas de ángulo/señal de control en tiempo real.
    """

    def __init__(self, connection_manager):
        """
        Args:
            connection_manager (ConnectionManager): Gestor de conexión compartido,
                usado para enviar la configuración PID al microcontrolador.
        """
        super().__init__()

        self.pid = PIDModel()  # Modelo que guarda las ganancias (Kp, Ki, Kd) y el modo (arriba/abajo)

        self.pid_plots = PIDPlots()  # Widget que dibuja las gráficas de ángulo y señal de control

        self.connection_manager = (
            connection_manager
        )

        self.setup_ui()  # Construye todos los elementos visuales de la pestaña

        self.counter = 0  # Contador usado para generar la señal simulada (ver simulate_pid)

        self.timer = QTimer()  # Temporizador que dispara la actualización periódica de las gráficas

        self.timer.timeout.connect(
            self.simulate_pid
        )

        # Simulacion pausada: los datos reales llegaran mediante telemetria.
        # self.timer.start(50)

    def setup_ui(self):
        """
        Construye y organiza todos los widgets de la pestaña: selección de
        punto de equilibrio, parámetros PID, estado del sistema, acciones
        y gráficas en tiempo real.
        """
        # =========================================================================================================================
        #                                                      Distribución/layout
        # =========================================================================================================================
        main_layout = QVBoxLayout()

        top_layout = QHBoxLayout()      # Fila superior: controles (izquierda) + gráficas (derecha)

        left_layout = QVBoxLayout()     # Columna izquierda: equilibrio + parámetros PID

        right_layout = QVBoxLayout()    # Columna derecha: gráficas

        bottom_layout = QHBoxLayout()   # Fila inferior: estado del sistema + acciones

        top_layout.addLayout(
            left_layout,
            1  # Proporción de espacio horizontal (1 parte de 3 en total junto con right_layout)
        )

        top_layout.addLayout(
            right_layout,
            2  # Ocupa el doble de espacio que left_layout (2 partes de 3)
        )

        main_layout.addLayout(
            top_layout
        )

        main_layout.addLayout(
            bottom_layout
        )

        # =========================================================================================================================
        #                                                      Punto de equilibrio
        # =========================================================================================================================

        equilibrium_group = QGroupBox(
            "Punto de Equilibrio"
        )

        equilibrium_layout = QVBoxLayout()

        self.down_radio = QRadioButton(
            "Abajo"
        )

        self.up_radio = QRadioButton(
            "Arriba"
        )

        self.down_radio.setChecked(True)  # Valor predeterminado: péndulo estabilizado hacia abajo

        self.mode_group = QButtonGroup()  # Agrupa los radio buttons para que sean mutuamente excluyentes

        self.mode_group.addButton(
            self.down_radio
        )

        self.mode_group.addButton(
            self.up_radio
        )

        equilibrium_layout.addWidget(
            self.down_radio
        )

        equilibrium_layout.addWidget(
            self.up_radio
        )

        equilibrium_group.setLayout(
            equilibrium_layout
        )

        # =========================================================================================================================
        #                                                      Parámetros PID
        # =========================================================================================================================
        pid_group = QGroupBox(
            "Parámetros del Controlador PID"
        )

        pid_layout = QFormLayout()

        self.kp = QLineEdit()  # Ganancia proporcional

        self.ki = QLineEdit()  # Ganancia integral

        self.kd = QLineEdit()  # Ganancia derivativa

        # Valores por defecto
        self.kp.setText("900")

        self.ki.setText("0.1")

        self.kd.setText("0.001")

        # Validador compartido: permite decimales entre -100000 y 100000, con hasta 6 decimales
        validator = QDoubleValidator(
            -100000.0,  # límite inferior
            100000.0,   # límite superior
            6           # cantidad de decimales permitidos
        )

        self.kp.setValidator(
            validator
        )

        self.ki.setValidator(
            validator
        )

        self.kd.setValidator(
            validator
        )

        pid_layout.addRow(
            "Kp",
            self.kp
        )

        pid_layout.addRow(
            "Ki",
            self.ki
        )

        pid_layout.addRow(
            "Kd",
            self.kd
        )

        pid_group.setLayout(
            pid_layout
        )

        # =========================================================================================================================
        #                                                      Estado
        # =========================================================================================================================
        status_group = QGroupBox(
            "Sistema de Control"
        )

        status_layout = QFormLayout()

        self.control_mode = QLabel(
            "PID"
        )

        self.control_status = QLabel()  # Etiqueta que refleja si el control PID está activo o inactivo

        set_status(self.control_status, STATUS_INACTIVE, STATUS_RED)  # Estado inicial: inactivo

        self.freq_status = QLabel(
            "---- Hz"  # Frecuencia de control, aún sin datos reales
        )

        status_layout.addRow(
            "Modo:",
            self.control_mode
        )

        status_layout.addRow(
            "Estado:",
            self.control_status
        )

        status_layout.addRow(
            "Frecuencia:",
            self.freq_status
        )

        status_group.setLayout(
            status_layout
        )

        # =========================================================================================================================
        #                                                      Acciones
        # =========================================================================================================================
        actions_group = QGroupBox("Acciones")

        actions_layout = QHBoxLayout()

        self.apply_button = QPushButton(
            "Guardar Configuración PID"
        )

        self.control_button = QPushButton(
            "Activar"
        )

        self.reset_button = QPushButton(
            "Reset"
        )

        self.apply_button.clicked.connect(
            self.save_pid
        )

        self.control_button.clicked.connect(self.toggle_pid)
        self.reset_button.clicked.connect(self.reset_pid)

        actions_layout.addWidget(
            self.apply_button
        )

        actions_layout.addWidget(
            self.control_button
        )

        actions_layout.addWidget(
            self.reset_button
        )

        actions_group.setLayout(
            actions_layout
        )

        # =========================================================================================================================
        #                                                      Estilo de los widgets
        # =========================================================================================================================

        set_control_height(
            self.kp,
            self.ki,
            self.kd
        )

        set_primary_button(
            self.apply_button,
        )

        set_secondary_button(
            self.control_button,
            self.reset_button
        )

        configure_layout(
            main_layout
        )

        configure_group_width(
            equilibrium_group
        )

        configure_group_width(
            pid_group
        )

        # =========================================================================================================================
        #                                                      Aplicar layout
        # =========================================================================================================================

        left_layout.addWidget(
            equilibrium_group
        )

        left_layout.addWidget(
            pid_group
        )

        right_layout.addWidget(
            self.pid_plots
        )

        bottom_layout.addWidget(
            status_group,
            1
        )

        bottom_layout.addWidget(
            actions_group,
            2
        )

        bottom_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        bottom_layout.setSpacing(8)

        self.setLayout(
            main_layout
        )

    def save_pid(self):
        """
        Valida las ganancias Kp, Ki y Kd ingresadas, guarda el modo de
        equilibrio seleccionado (arriba/abajo) en el modelo PID, y envía
        la configuración resultante al microcontrolador.

        Si alguna ganancia no es válida según su validador, se muestra una
        advertencia y se detiene el proceso sin enviar datos.
        """

        # Ganancias del controlador
        if not self.kp.hasAcceptableInput():
            QMessageBox.warning(
                self,
                "Error",
                "Kp inválido"
            )
            return
        self.pid.kp = float(
            self.kp.text()
        )

        if not self.ki.hasAcceptableInput():
            QMessageBox.warning(
                self,
                "Error",
                "Ki inválido"
            )
            return
        self.pid.ki = float(
            self.ki.text()
        )

        if not self.kd.hasAcceptableInput():
            QMessageBox.warning(
                self,
                "Error",
                "Kd inválido"
            )
            return
        self.pid.kd = float(
            self.kd.text()
        )

        # Modo/posición de equilibrio del péndulo
        if self.down_radio.isChecked():
            self.pid.mode = (
                PIDModel.DOWN
            )

        else:
            self.pid.mode = (
                PIDModel.UP
            )

        # Envío del modelo PID al microcontrolador
        print(self.pid.to_json())  # Depuración: muestra en consola el JSON enviado

        payload = {"type": "pid_config", "equilibrium": self.pid.mode,
                   "kp": self.pid.kp, "ki": self.pid.ki, "kd": self.pid.kd}
        self.connection_manager.send(json.dumps(payload, separators=(",", ":")))

    def simulate_pid(self):
        """
        Genera una señal simulada de ángulo y señal de control (mientras no
        se reciban datos reales del hardware en esta pestaña) y actualiza
        las gráficas de PIDPlots.

        Se ejecuta periódicamente mediante self.timer (cada 50 ms).
        """
        self.counter += 1

        t = self.counter / 15

        angle = 15 * math.sin(t)  # Ángulo simulado: oscilación senoidal de amplitud 15°

        control = (
            1000 * math.sin(t)      # Componente principal de la señal de control simulada
            +
            150 * math.sin(4 * t)   # Componente de mayor frecuencia, simula ruido/dinámica secundaria
        )

        self.pid_plots.update_plots(
            angle,
            control
        )
    def toggle_pid(self):
        if not self.connection_manager.connected:
            QMessageBox.warning(self, "Sin conexion", "Conecta el ESP32 primero.")
            return
        command = "stop" if self.control_button.text() == "Desactivar" else "start_pid"
        self.connection_manager.send(json.dumps({"type":"command", "command":command}))

    def reset_pid(self):
        if not self.connection_manager.connected:
            QMessageBox.warning(self, "Sin conexion", "Conecta el ESP32 primero.")
            return
        self.connection_manager.send(json.dumps({"type":"command", "command":"reset"}))

    def apply_control_status(self, state, control_mode):
        active = state == "running" and control_mode == "pid"
        self.control_button.setText("Desactivar" if active else "Activar")
        set_status(self.control_status, STATUS_ACTIVE if active else STATUS_INACTIVE,
                   STATUS_GREEN if active else STATUS_RED)
