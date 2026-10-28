"""
Módulo de la ventana principal de la aplicación.

Define la clase MainWindow, encargada de construir la interfaz gráfica
principal: organiza las pestañas de configuración, control PID y control
por retroalimentación de estado, y coordina la comunicación con el
hardware a través del ConnectionManager.
"""

from PySide6.QtWidgets import (
    QMainWindow,  # Ventana principal de la aplicación (provee barra de menú, barra de estado, widget central, etc.)
    QWidget,      # Widget genérico, usado aquí como contenedor central
    QTabWidget,   # Contenedor que organiza el contenido en pestañas
    QVBoxLayout   # Organiza los widgets hijos en una columna vertical
)

from PySide6.QtWidgets import QMessageBox
import json
import math
from PySide6.QtGui import QIcon  # Permite cargar y asignar el ícono de la ventana

# Pestañas (vistas) de la interfaz, una clase por cada modo de control
from ui.config_tab import ConfigTab  # Pestaña de configuración de conexión
from ui.pid_tab import PIDTab        # Pestaña de control PID
from ui.state_tab import StateTab    # Pestaña de control por retroalimentación de estado

from comunicacion.connection_manager import (
    ConnectionManager  # Gestiona la conexión y comunicación con el hardware (serial/bluetooth/etc.)
)
from models.state_model import StateModel  # Modelo de datos que almacena el estado actual del péndulo


class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación.

    Se encarga de:
        - Inicializar el gestor de conexión y el modelo de estado.
        - Construir el layout general de la interfaz.
        - Crear y organizar las pestañas de configuración, PID y control de estado.
        - Recibir los datos entrantes del hardware y distribuirlos al modelo
          y a la vista correspondiente.
    """

    def __init__(self):
        """
        Constructor de la ventana principal.

        Se ejecuta automáticamente al instanciar la clase. Inicializa los
        gestores de datos/conexión, configura la ventana y construye
        todas las pestañas de la interfaz.
        """
        super().__init__()  # Inicializa la clase base QMainWindow con su configuración por defecto

        # =========================================================================================================================
        #                                                 Coordinación de actividades
        # =========================================================================================================================

        # Gestor de conexión: maneja el envío/recepción de datos con el sistema físico
        self.connection_manager = ConnectionManager()

        # Modelo de datos: almacena el estado actual del péndulo (ángulo, posición, velocidades, etc.)
        self.state_model = StateModel()

        # Conecta la señal de datos recibidos al método que procesa la información entrante
        self.connection_manager.data_received.connect(
            self.process_received_data
        )
        self.connection_manager.connection_changed.connect(
            self.on_connection_changed
        )

        # =========================================================================================================================
        #                                                     Ventana
        # =========================================================================================================================

        # Título de la ventana, visible en la barra superior del sistema operativo
        self.setWindowTitle(
            "Control de Péndulo Invertido"
        )

        # Ícono de la aplicación
        self.setWindowIcon(
            QIcon("resources/icon.png")
        )

        # Tamaño inicial de la ventana (ancho, alto) en píxeles
        self.resize(900, 400)

        # Widget central: contenedor que alojará todos los elementos visuales (pestañas, botones, gráficas)
        # Nota: en Qt, el contenido no se agrega directamente a la ventana, sino a este widget central
        self.central_widget = QWidget()
        self.setCentralWidget(  # Define este widget como el contenedor principal de la ventana
            self.central_widget
        )

        # Layout vertical: organiza los elementos del widget central en una columna
        self.layout = QVBoxLayout()

        self.central_widget.setLayout(  # Asigna el layout vertical al widget central
            self.layout
        )

        # Widget de pestañas: permite alternar entre las distintas vistas de control
        self.tabs = QTabWidget()

        self.layout.addWidget(  # Agrega el widget de pestañas al layout principal
            self.tabs
        )

        # -------------------------------------------------------------------------------------------------------------------
        # Creación de las pestañas de la interfaz
        # -------------------------------------------------------------------------------------------------------------------

        self.config_tab = ConfigTab(
            self.connection_manager
        )  # Pestaña de configuración (conexión con el hardware)

        self.pid_tab = PIDTab(
            self.connection_manager
        )  # Pestaña de control PID

        self.state_tab = StateTab(
            self.connection_manager,
            self.state_model
        )  # Pestaña de control por retroalimentación de estado

        # Registra cada pestaña en el QTabWidget, con su respectiva etiqueta visible
        self.tabs.addTab(
            self.config_tab,
            "Configuración"
        )

        self.tabs.addTab(
            self.pid_tab,
            "Control PID"
        )

        self.tabs.addTab(
            self.state_tab,
            "Control por Retroalimentación de Estado"
        )

    def on_connection_changed(self, connected):
        """Solicita telemetria por el transporte activo; nunca inicia el motor."""
        if connected:
            self.connection_manager.send(json.dumps({
                "type": "command", "command": "telemetry", "enabled": True
            }, separators=(",", ":")))
        else:
            self.pid_tab.apply_control_status("ready", "none")
            self.state_tab.apply_control_status("ready", "none")
            self.state_model.clear()
            self.state_tab.update_ui()

    def process_received_data(self, data):
        if not isinstance(data, dict):
            return
        kind = data.get("type")
        if kind == "telemetry":
            self.state_model.update_from_telemetry(data)
            self.state_tab.refresh()
            self.pid_tab.pid_plots.update_plots(
                self.state_model.angle,
                self._number_or_none(data.get("control_effort_steps_s"))
            )
        elif kind == "status" and "state" in data:
            self.pid_tab.apply_control_status(
                data.get("state", "ready"), data.get("control_mode", "none")
            )
            self.state_tab.apply_control_status(
                data.get("state", "ready"), data.get("control_mode", "none")
            )
        elif kind == "error":
            QMessageBox.warning(self, "Respuesta del ESP32",
                                f"{data.get('code', 'ERROR')}: {data.get('message', '')}")
        elif kind == "ack":
            print("[ACK]", data.get("for"), data.get("command", ""))

    @staticmethod
    def _number_or_none(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        number = float(value)
        return number if math.isfinite(number) else None
