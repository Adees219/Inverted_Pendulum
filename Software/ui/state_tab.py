"""
Pestaña de control por retroalimentación de estado.

Define la clase StateTab, encargada de:
    - Mostrar en tiempo real las variables de estado del péndulo (ángulo,
      velocidad angular, posición y velocidad lineal).
    - Permitir configurar las ganancias del controlador (K1-K4) y la
      referencia (posición objetivo) del carro.
    - Mostrar el estado del sistema de control y graficar las variables
      de estado mediante StatePlots.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QHBoxLayout,
    QGridLayout,
    QPushButton
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

from plots.state_plots import (
    StatePlots  # Widget de gráficas para visualizar las variables de estado en tiempo real
)

# TEMPORAL: usado anteriormente para simulación de datos (ver método simulate_data, comentado más abajo)
from PySide6.QtCore import (
    QTimer
)
import math
import json


class StateTab(QWidget):
    """
    Pestaña de control por retroalimentación de estado.

    Agrupa los controles para visualizar las variables de estado del
    péndulo, configurar las ganancias del controlador y la referencia
    del carro, y muestra el estado general del sistema de control.
    """

    def __init__(self, connection_manager, state_model):
        """
        Args:
            connection_manager (ConnectionManager): Gestor de conexión compartido,
                usado para enviar la configuración al microcontrolador.
            state_model (StateModel): Modelo que almacena los valores actuales
                de las variables de estado del péndulo (ángulo, posición, etc.).
        """
        super().__init__()

        self.state_plots = StatePlots()  # Widget que dibuja las gráficas de las variables de estado

        self.connection_manager = connection_manager

        self.state = state_model  # Referencia al modelo de estado compartido con MainWindow

        self.setup_ui()  # Construye todos los elementos visuales de la pestaña

        # Timer reservado para una eventual actualización periódica (actualmente sin uso activo,
        # ya que simulate_data está deshabilitado más abajo)
        self.timer = QTimer()

        # NOTA: bloque de simulación de datos deshabilitado. Se dejó comentado como referencia
        # por si se necesita reactivar una simulación de prueba sin datos reales del hardware.
        #     self.timer.timeout.connect(
        #         self.simulate_data
        #     )
        #    # self.timer.start(100)
        #     self.counter = 0

    def setup_ui(self):
        """
        Construye y organiza todos los widgets de la pestaña: variables de
        estado, ganancias del controlador, referencia del carro, estado del
        sistema, acciones del controlador y gráficas en tiempo real.
        """
        # =========================================================================================================================
        #                                                      Distribución/layout
        # =========================================================================================================================

        main_layout = QVBoxLayout()

        top_layout = QHBoxLayout()      # Fila superior: controles (izquierda) + gráficas (derecha)

        left_layout = QVBoxLayout()     # Columna izquierda: estado, ganancias y referencia

        right_layout = QVBoxLayout()    # Columna derecha: gráficas

        bottom_layout = QHBoxLayout()   # Fila inferior: estado del sistema + controlador (acciones)

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
        #                                                      Variables de estado
        # =========================================================================================================================

        state_group = QGroupBox(
            "Variables de Estado"
        )

        state_layout = QFormLayout()

        self.angle_label = QLabel(
            "0.00 °"
        )

        self.angular_velocity_label = QLabel(
            "0.00 °/s"
        )

        self.position_label = QLabel(
            "0.00 mm"
        )

        self.linear_velocity_label = QLabel(
            "0.00 mm/s"
        )

        state_layout.addRow(
            "Ángulo:",
            self.angle_label
        )

        state_layout.addRow(
            "Vel. Angular:",
            self.angular_velocity_label
        )

        state_layout.addRow(
            "Posición:",
            self.position_label
        )

        state_layout.addRow(
            "Vel. Lineal:",
            self.linear_velocity_label
        )

        state_group.setLayout(
            state_layout
        )

        # =========================================================================================================================
        #                                                      Ganancias del controlador
        # =========================================================================================================================

        gains_group = QGroupBox(
            "Ganancias del Controlador"
        )

        gains_layout = QGridLayout()  # Organiza las ganancias en una cuadrícula de 2 filas x 4 columnas (etiqueta+campo x2)

        # Campos de entrada para las 4 ganancias del controlador por realimentación de estado
        self.k1 = QLineEdit()
        self.k2 = QLineEdit()
        self.k3 = QLineEdit()
        self.k4 = QLineEdit()

        # Valores predeterminados/iniciales
        self.k1.setText("0.0")
        self.k2.setText("0.0")
        self.k3.setText("0.0")
        self.k4.setText("0.0")

        # Fila 0: K1 y K2
        gains_layout.addWidget(
            QLabel("K1"),
            0, 0
        )
        gains_layout.addWidget(
            self.k1,
            0, 1
        )

        gains_layout.addWidget(
            QLabel("K2"),
            0, 2
        )
        gains_layout.addWidget(
            self.k2,
            0, 3
        )

        # Fila 1: K3 y K4
        gains_layout.addWidget(
            QLabel("K3"),
            1, 0
        )

        gains_layout.addWidget(
            self.k3,
            1, 1
        )

        gains_layout.addWidget(
            QLabel("K4"),
            1, 2
        )

        gains_layout.addWidget(
            self.k4,
            1, 3
        )

        gains_group.setLayout(
            gains_layout
        )

        # =========================================================================================================================
        #                                                      Referencia del carro
        # =========================================================================================================================

        reference_group = QGroupBox(
            "Referencia del Carro"
        )

        reference_layout = QFormLayout()

        self.reference = QLineEdit()  # Posición objetivo (referencia) que debe alcanzar el carro

        reference_layout.addRow(
            "Posición Objetivo (mm)",
            self.reference
        )

        reference_group.setLayout(
            reference_layout
        )

        # =========================================================================================================================
        #                                                      Estado del sistema
        # =========================================================================================================================

        status_group = QGroupBox(
            "Sistema de Control"
        )

        status_layout = QFormLayout()

        self.control_mode = QLabel(
            "Estado"
        )

        status_layout.addRow(
            "Modo:",
            self.control_mode
        )

        self.control_status = QLabel(
            "● Inactivo"
        )

        set_status(self.control_status, STATUS_INACTIVE, STATUS_RED)  # Estado inicial: inactivo (rojo)

        self.last_update = QLabel(
            "---"  # Marca de tiempo de la última actualización recibida (sin datos aún)
        )

        status_layout.addRow(
            "Estado:",
            self.control_status
        )

        status_layout.addRow(
            "Última actualización",
            self.last_update
        )

        status_group.setLayout(
            status_layout
        )

        # =========================================================================================================================
        #                                                      Controlador (acciones)
        # =========================================================================================================================

        controller_group = QGroupBox(
            "Controlador"
        )

        controller_layout = QVBoxLayout()

        self.update_button = QPushButton(
            "Guardar Configuración"
        )

        buttons_layout = QHBoxLayout()  # Layout secundario para agrupar los botones de control lado a lado

        self.control_button = QPushButton(
            "Activar Control"
        )

        self.reset_button = QPushButton(
            "Reset"
        )

        buttons_layout.addWidget(
            self.control_button
        )

        buttons_layout.addWidget(
            self.reset_button
        )

        controller_layout.addWidget(
            self.update_button
        )

        controller_layout.addLayout(
            buttons_layout
        )

        controller_group.setLayout(
            controller_layout
        )

        self.update_button.clicked.connect(self.save_state_config)
        self.control_button.clicked.connect(self.toggle_state_control)
        self.reset_button.clicked.connect(self.reset_state_control)

        # =========================================================================================================================
        #                                                      Estilo de los widgets
        # =========================================================================================================================

        set_control_height(
            self.k1,
            self.k2,
            self.k3,
            self.k4,
            self.reference
        )

        set_primary_button(
            self.update_button
        )

        set_secondary_button(
            self.control_button,
            self.reset_button
        )

        configure_layout(
            main_layout
        )

        # =========================================================================================================================
        #                                                      Aplicar layout
        # =========================================================================================================================

        left_layout.addWidget(
            state_group
        )

        left_layout.addWidget(
            gains_group
        )

        left_layout.addWidget(
            reference_group
        )

        left_layout.addStretch()  # Empuja los grupos hacia arriba, dejando espacio vacío al final de la columna

        right_layout.addWidget(
            self.state_plots
        )

        bottom_layout.addWidget(
            status_group,
            1
        )

        bottom_layout.addWidget(
            controller_group,
            2
        )

        self.setLayout(
            main_layout
        )

        # =========================================================================================================================
        #                                               Actualización inicial de valores
        # =========================================================================================================================

        self.update_ui()  # Refleja en las etiquetas los valores iniciales del modelo de estado

    def update_ui(self):
        """
        Actualiza el texto de las etiquetas de variables de estado (ángulo,
        velocidad angular, posición y velocidad lineal) con los valores
        actuales almacenados en self.state.
        """
        self.angle_label.setText(
            f"{self.state.angle:.2f} °" if self.state.angle is not None else "N/D"
        )

        self.angular_velocity_label.setText(
            f"{self.state.angular_velocity:.2f} °/s" if self.state.angular_velocity is not None else "N/D"
        )

        self.position_label.setText(
            f"{self.state.position:.2f} mm" if self.state.position is not None else "N/D"
        )

        self.linear_velocity_label.setText(
            f"{self.state.linear_velocity:.2f} mm/s" if self.state.linear_velocity is not None else "N/D"
        )

    # NOTA: método de simulación deshabilitado. Se usaba para generar datos de
    # prueba (ángulo, velocidad angular, posición y velocidad lineal como
    # funciones senoidales/cosenoidales) antes de contar con datos reales del
    # hardware. Se conserva comentado como referencia para pruebas futuras.
    #
    # def simulate_data(self):
    #
    #     self.counter+=1
    #     t = self.counter/10
    #
    #     self.state.angle = (
    #         20* math.sin(t)
    #     )
    #
    #     self.state.angular_velocity = (
    #         20 * math.cos(t)
    #     )
    #
    #     self.state.position = (
    #         200 * math.sin(t/2)
    #     )
    #
    #     self.state.linear_velocity = (
    #         100 * math.cos(t/2)
    #     )
    #
    #     self.refresh()

    def refresh(self):
        """
        Actualiza tanto las etiquetas de variables de estado como las
        gráficas de StatePlots con los valores actuales del modelo de estado.

        Este método es llamado externamente (desde MainWindow) cada vez que
        llegan nuevos datos del hardware.
        """
        self.update_ui()

        self.state_plots.update_plots(
            self.state
        )
    def save_state_config(self):
        if not self.connection_manager.connected:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Sin conexion", "Conecta el ESP32 primero.")
            return
        try:
            values = [float(w.text()) for w in (self.k1, self.k2, self.k3, self.k4)]
            reference = float(self.reference.text())
            if not all(math.isfinite(v) for v in values + [reference]):
                raise ValueError("Valores no finitos")
        except ValueError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Parametros invalidos", "Revisa K1-K4 y la referencia en mm.")
            return
        payload = {"type":"state_config", "k1":values[0], "k2":values[1],
                   "k3":values[2], "k4":values[3], "reference_mm":reference}
        self.connection_manager.send(json.dumps(payload, separators=(",", ":")))

    def toggle_state_control(self):
        if not self.connection_manager.connected:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Sin conexion", "Conecta el ESP32 primero.")
            return
        command = "stop" if self.control_button.text() == "Desactivar" else "start_state"
        self.connection_manager.send(json.dumps({"type":"command", "command":command}))

    def reset_state_control(self):
        if not self.connection_manager.connected:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Sin conexion", "Conecta el ESP32 primero.")
            return
        self.connection_manager.send(json.dumps({"type":"command", "command":"reset"}))

    def apply_control_status(self, state, control_mode):
        active = state == "running" and control_mode == "state"
        self.control_button.setText("Desactivar" if active else "Activar Control")
        set_status(self.control_status, STATUS_ACTIVE if active else STATUS_INACTIVE,
                   STATUS_GREEN if active else STATUS_RED)
