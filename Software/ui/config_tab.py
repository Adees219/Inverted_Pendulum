"""
Pestaña de configuración de la interfaz.

Define la clase ConfigTab, encargada de:
    - Permitir seleccionar el método de conexión con el hardware (Serial o Red/TCP-IP).
    - Establecer y validar los parámetros de configuración del sistema
      (amperaje, microstep, velocidad máxima, aceleración, períodos de
      control/telemetría y offset del sensor AS5600).
    - Enviar la configuración validada al microcontrolador a través del
      ConnectionManager.
"""

from PySide6.QtWidgets import (  # Widgets de Qt utilizados para construir la interfaz
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox
)

from ui.utils.widget_style import *  # Funciones auxiliares de estilo (dimensiones, colores, fuentes de los widgets)

from comunicacion.network_config import (  # Parámetros de la red TCP/IP compartidos por la aplicación
    NETWORK_BASE,     # Prefijo de la dirección IP de la red (p. ej. "192.168.12.")
    build_device_ip   # Función que arma y valida la IP completa a partir del número de equipo
)

from ui.constants.ui_constants import (  # Colores estándar para indicar el estado de conexión
    STATUS_GREEN,
    STATUS_RED,
    STATUS_YELLOW
)

from PySide6.QtGui import (  # Validadores para restringir el texto ingresado en los campos numéricos
    QIntValidator,
    QDoubleValidator
)

from PySide6.QtNetwork import QAbstractSocket  # Permite consultar el estado del socket TCP (p. ej. ConnectingState)
from models.config_model import ConfigModel  # Modelo que almacena y serializa los parámetros de configuración


class ConfigTab(QWidget):
    """
    Pestaña de configuración.

    Contiene los controles para elegir el modo de conexión (Serial/Red),
    establecer los parámetros del sistema y enviarlos al microcontrolador.
    """

    def __init__(self, connection_manager):
        """
        Args:
            connection_manager (ConnectionManager): Gestor de conexión compartido
                con el resto de la aplicación, usado para conectar/desconectar
                y enviar la configuración al hardware.
        """
        super().__init__()

        self.connection_manager = (
            connection_manager
        )  # Referencia al gestor de comunicación (serial/red)

        # Cuando el estado de conexión cambia en el connection_manager, se actualiza la interfaz
        self.connection_manager.connection_changed.connect(
            self.update_connection_status
        )

        # Si ocurre un error en la conexión serial, se muestra un mensaje al usuario
        self.connection_manager.serial_manager.connection_error.connect(
            self.show_connection_error
        )

        # Lo mismo para los errores de la conexión TCP (host inaccesible, timeout, mensajes inválidos, etc.)
        self.connection_manager.tcp_manager.connection_error.connect(
            self.show_connection_error
        )

        # Mientras se intenta conectar por TCP, se actualiza la interfaz (estado "Conectando...", botón "Cancelar")
        self.connection_manager.connecting_changed.connect(
            self.update_connecting_status
        )

        self.config = ConfigModel()  # Modelo que almacena los valores de configuración a enviar

        self.setup_ui()  # Construye todos los elementos visuales de la pestaña

    def setup_ui(self):
        """
        Construye y organiza todos los widgets de la pestaña: grupo de método
        de conexión, grupo TCP/IP, grupo Serial y grupo de configuración general.
        """

        # Layout principal (organiza los grupos verticalmente)
        main_layout = QVBoxLayout()

        # =========================================================================================================================
        #                                                      Método de conexión
        # =========================================================================================================================
        conec_group = QGroupBox("Método de Conexión")  # Recuadro con borde y título

        conec_form = QFormLayout()
        radio_layout = QHBoxLayout()

        # Radio buttons para elegir el método de conexión (mutuamente excluyentes)
        self.serial_radio = QRadioButton("Serial")
        self.network_radio = QRadioButton("Red")

        radio_layout.addWidget(
            self.serial_radio
        )

        radio_layout.addWidget(
            self.network_radio
        )

        # Se agrupan los radio buttons en un widget para poder insertarlos como una sola fila en el formulario
        radio_widget = QWidget()
        radio_widget.setLayout(
            radio_layout
        )

        self.connection_status = QLabel()  # Etiqueta que muestra el estado actual de la conexión

        set_status(self.connection_status, "● Desconectado", STATUS_RED)  # Estado inicial: desconectado (rojo)

        conec_form.addRow(
            "Estado",
            self.connection_status
        )

        conec_form.addRow(
            "Modo:",
            radio_widget
        )

        conec_group.setLayout(
            conec_form
        )

        # ==================================================================================================================================
        #                                                            RED/Internet (TCP/IP)
        # ==================================================================================================================================

        self.TCP_group = QGroupBox("TCP/IP")

        TCP_layout = QFormLayout()

        self.TCP_label = QLabel(
            f"{NETWORK_BASE}XX"  # Muestra el formato esperado de la IP (referencia visual, no editable)
        )

        self.TCP_Equipo = QLineEdit()  # Campo donde el usuario ingresa el número de equipo (últimos octetos de la IP)

        self.TCP_boton = QPushButton(
            "Conectar"
        )

        self.TCP_boton.clicked.connect(
            self.handle_connect
        )

        TCP_layout.addRow(
            "Dirección IP:",
            self.TCP_label
        )

        TCP_layout.addRow(
            "No. Equipo:",
            self.TCP_Equipo
        )

        TCP_layout.addRow(
            self.TCP_boton
        )

        self.TCP_group.setLayout(
            TCP_layout
        )

        # ==================================================================================================================================
        #                                                               Puerto COM
        # ==================================================================================================================================

        self.com_group = QGroupBox("Serial")  # Recuadro que agrupa los controles de conexión serial

        com_layout = QFormLayout()

        self.com_combo = QComboBox()  # Lista desplegable con los puertos COM disponibles

        ports = (
            self.connection_manager  # Se accede al gestor de conexión
            .serial_manager           # ...específicamente al submódulo encargado del puerto serial
            .get_available_ports()    # ...y se obtiene la lista de puertos disponibles en el sistema
        )

        self.com_combo.addItems(  # Se cargan los puertos encontrados en el combo box
            ports
        )

        self.refresh_button = QPushButton(
            "Actualizar"
        )

        self.refresh_button.clicked.connect(  # Al presionar, se vuelve a escanear los puertos disponibles
            self.refresh_ports
        )

        self.serial_button = QPushButton(
            "Conectar"
        )

        self.serial_button.clicked.connect(  # Al presionar, conecta o desconecta según el estado actual
            self.handle_connect
        )

        com_layout.addRow(
            "Puerto COM",
            self.com_combo
        )

        com_layout.addRow(
            self.refresh_button
        )

        com_layout.addRow(
            self.serial_button
        )

        self.com_group.setLayout(
            com_layout
        )

        # ========================================================================================================================
        #                                                 Configuración general
        # ========================================================================================================================

        config_group = QGroupBox(
            "Configuración"
        )

        form_layout = QFormLayout()  # Organiza automáticamente pares de etiqueta + campo

        self.amperaje = QLineEdit()

        self.microstep = QComboBox()

        self.microstep.addItems(
            ["128", "64", "32", "16", "8", "4", "2", "1"]  # Valores de microstepping soportados por el driver TMC2209
        )

        self.microstep.setCurrentIndex(3)  # "16" como valor predeterminado (índice 3 de la lista)

        self.velocidad_maxima = QLineEdit()

        self.aceleracion = QLineEdit()

        self.control_period_us = QLineEdit()

        self.telemetry_period_ms = QLineEdit()

        self.offset_AS5600 = QLineEdit()

        # ************************************** Valores predeterminados *************************************
        self.amperaje.setText(
            "800"  # mA (motor 17HD40005H-22B soporta hasta 1.6 A máx.)
        )
        
        self.TCP_Equipo.setText("01")  # Número de equipo predeterminado (último octeto de la IP)

        self.velocidad_maxima.setText(
            "32000"  # steps/s (rango máximo permitido: ±32000)
        )

        self.aceleracion.setText(
            "150000"  # steps/s^2
        )

        self.control_period_us.setText(
            "1000"  # microsegundos
        )

        self.telemetry_period_ms.setText(
            "20"  # milisegundos
        )

        self.offset_AS5600.setText(
            "283"  # grados
        )

        # ************************************** Validadores de texto *************************************
        self.amperaje.setValidator(  # Restringe la entrada a enteros dentro del rango permitido
            QIntValidator(
                300,
                1600
            )
        )

        self.TCP_Equipo.setValidator(  # El último octeto de una IP de host válida va de 1 a 254 (0 = red, 255 = broadcast)
            QIntValidator(1, 254)
        )

        self.velocidad_maxima.setValidator(
            QIntValidator(
                300,
                100000
            )
        )

        self.aceleracion.setValidator(
            QIntValidator(
                300,
                150000
            )
        )

        self.offset_AS5600.setValidator(  # Permite decimales, con hasta 3 cifras después del punto
            QDoubleValidator(
                0.0,
                360,
                3
            )
        )

        self.control_period_us.setValidator(
            QIntValidator(
                500,
                100000
            )
        )

        self.telemetry_period_ms.setValidator(
            QIntValidator(
                10,
                1000
            )
        )
        # ****************************************************************************************************

        # Se agregan los campos (etiqueta + control) al formulario del grupo de configuración
        form_layout.addRow(
            "Amperaje (mA)",
            self.amperaje
        )

        form_layout.addRow(
            "Microstep",
            self.microstep
        )

        form_layout.addRow(
            "Velocidad Máxima",
            self.velocidad_maxima
        )

        form_layout.addRow(
            "Aceleración",
            self.aceleracion
        )

        form_layout.addRow(
            "Período de control (µs)",
            self.control_period_us
        )

        form_layout.addRow(
            "Período de Telemetría (ms)",
            self.telemetry_period_ms  
        )

        form_layout.addRow(
            "Offset AS5600",
            self.offset_AS5600
        )

        self.modify_button = QPushButton(
            "Guardar Configuración"
        )

        self.modify_button.clicked.connect(
            self.save_config
        )

        form_layout.addRow(
            self.modify_button
        )

        config_group.setLayout(
            form_layout
        )

        # ************************************** Juntando cuadros de conexión (Serial + TCP/IP) *******************************
        layout_tipos_conexiones = QHBoxLayout()

        layout_tipos_conexiones.addWidget(
            self.com_group,
            1  # Proporción de espacio que ocupa el widget dentro del layout (aquí, 50% junto al otro grupo)
        )

        layout_tipos_conexiones.addWidget(
            self.TCP_group,
            1
        )

        # ========================================================================================================
        #                                          Estilo de los widgets
        # ========================================================================================================

        # Altura uniforme para todos los QLineEdit y QComboBox de la pestaña
        set_control_height(
            self.amperaje,
            self.microstep,
            self.velocidad_maxima,
            self.aceleracion,
            self.control_period_us,
            self.telemetry_period_ms,
            self.offset_AS5600,
            self.com_combo,
            self.TCP_Equipo
        )

        # Estilo de botones
        set_primary_button(self.modify_button)
        set_secondary_button(
            self.TCP_boton,
            self.refresh_button,
            self.serial_button
        )

        # Espaciado y márgenes del layout principal y del sub-layout de conexiones
        configure_layout(
            main_layout
        )

        configure_sub_layout(
            layout_tipos_conexiones
        )

        # ========================================================================================================
        #                                          Agregar al layout principal
        # ========================================================================================================
        # Nota: los grupos (conec_group, com_group, TCP_group, config_group) ya tienen su
        # propio layout interno, pero eso no los hace visibles por sí solos; deben añadirse
        # al layout principal de la pestaña para aparecer en la ventana.

        main_layout.addWidget(
            conec_group
        )

        main_layout.addLayout(
            layout_tipos_conexiones
        )

        main_layout.addWidget(
            config_group
        )

        main_layout.addStretch()  # Empuja todo el contenido hacia arriba, dejando espacio vacío abajo

        self.setLayout(
            main_layout
        )

        # **************************** Habilitar/deshabilitar grupos según el modo elegido *******************************
        self.serial_radio.setChecked(True)  # Modo Serial seleccionado por defecto

        # Al cambiar la selección de cualquiera de los radio buttons, se actualiza qué grupo está habilitado
        self.serial_radio.toggled.connect(
            self.actualizar_metodo_conexion
        )

        self.network_radio.toggled.connect(
            self.actualizar_metodo_conexion
        )

        self.actualizar_metodo_conexion()  # Se ejecuta una vez al iniciar para dejar la interfaz en el estado correcto
        # ********************************************************************************************************

    def actualizar_metodo_conexion(self):
        """
        Habilita el grupo de controles correspondiente al método de conexión
        seleccionado (Serial o TCP/IP) y deshabilita el otro.
        """
        if self.serial_radio.isChecked():

            self.com_group.setEnabled(True)

            self.TCP_group.setEnabled(False)

        else:

            self.com_group.setEnabled(False)

            self.TCP_group.setEnabled(True)

    def handle_connect(self):
        """
        Conecta o desconecta el sistema según el estado actual de la conexión.

        Si hay un intento de conexión TCP en curso, lo cancela. Si no hay
        conexión activa, arma el "target" (puerto serial o IP) según el modo
        seleccionado y solicita al connection_manager que se conecte. Si ya
        existe una conexión, la termina.
        """
        # Caso especial: si se está intentando conectar por red, el botón actúa como "Cancelar"
        if (
            self.connection_manager.current_mode
            == self.connection_manager.NETWORK
            and
            self.connection_manager.tcp_manager.socket.state()
            == QAbstractSocket.ConnectingState
        ):
            self.connection_manager.disconnect()
            return

        if not self.connection_manager.connected:  # Si actualmente no está conectado

            if self.serial_radio.isChecked():

                self.connection_manager.set_mode(  # Indica al gestor que use modo Serial
                    self.connection_manager.SERIAL
                )

                target = (
                    self.com_combo.currentText()  # Puerto COM seleccionado en el combo box
                )

            else:
          

                self.connection_manager.set_mode(  # Indica al gestor que use modo Red
                    self.connection_manager.NETWORK
                )

                try:
                    device_number = int(
                        self.TCP_Equipo.text()  # Número de equipo ingresado por el usuario
                    )

                    target = build_device_ip(  # Arma la IP completa; lanza ValueError si el número es inválido
                        device_number
                    )

                except ValueError as error:  # Número de equipo vacío o fuera de rango: se avisa y se cancela la conexión

                    QMessageBox.warning(
                        self,
                        "Número de equipo inválido",
                        str(error)
                    )

                    return

            self.connection_manager.connect(  # El connection_manager decide el método según el modo y realiza la conexión
                target
            )

        else:

            self.connection_manager.disconnect()  # Si ya está conectado, se desconecta


    def refresh_ports(self):
        """Vuelve a escanear y actualizar la lista de puertos COM disponibles."""
        self.com_combo.clear()  # Limpia la lista actual antes de recargarla

        ports = (
            self.connection_manager
            .get_available_ports()
        )

        self.com_combo.addItems(
            ports
        )

    def update_connection_status(self, connected):
        """
        Actualiza los indicadores visuales (etiqueta de estado, texto de
        botones y habilitación de controles) según el estado de conexión.

        Args:
            connected (bool): True si el sistema está conectado, False si no.
        """
        

        if connected:

            set_status(self.connection_status, "● Conectado", STATUS_GREEN)

            self.serial_button.setText(  # El botón cambia de "Conectar" a "Desconectar"
                "Desconectar"
            )

            self.TCP_boton.setText(
                "Desconectar"
            )

            self.com_combo.setEnabled(False)  # Se bloquea el cambio de puerto mientras hay una conexión activa
            self.TCP_Equipo.setEnabled(False)

        else:

            set_status(self.connection_status, "● Desconectado", STATUS_RED)

            self.serial_button.setText(
                "Conectar"
            )

            self.TCP_boton.setText(
                "Conectar"
            )

            self.com_combo.setEnabled(True)
            self.TCP_Equipo.setEnabled(True)

    def show_connection_error(self, message):
        """Muestra un cuadro de diálogo con el mensaje de error de conexión recibido."""
        QMessageBox.critical(self, "Error de conexión", message)

    def save_config(self):
        """
        Valida y guarda los parámetros de configuración ingresados por el
        usuario, y los envía al microcontrolador a través del connection_manager.

        Si algún campo no cumple con su rango permitido, se muestra una
        advertencia y se detiene el proceso sin enviar datos.
        """

        # Amperaje
        if not self.amperaje.hasAcceptableInput():  # Verifica que el valor esté dentro del rango definido por el validador
            QMessageBox.warning(
                self,
                "Amperaje Invalido",
                "Valores permitidos: 300 - 1600 mA"
            )
            return
        self.config.amperaje = int(
            self.amperaje.text()
        )

        # Microstep
        self.config.microstep = int(
            self.microstep.currentText()
        )

        # Velocidad máxima
        if not self.velocidad_maxima.hasAcceptableInput():
            QMessageBox.warning(self, "Velocidad Máxima Invalida", "Valores permitidos: 300 - 100000 steps/s")
            return
        self.config.velocidad_maxima = int(
            self.velocidad_maxima.text()
        )

        # Aceleración
        if not self.aceleracion.hasAcceptableInput():
            QMessageBox.warning(self, "Aceleracion Invalida", "Valores permitidos: 300 - 150000 steps/s^2")
            return
        self.config.aceleracion = int(
            self.aceleracion.text()
        )

        # Período de control
        if not self.control_period_us.hasAcceptableInput():
            QMessageBox.warning(self, "Período de Control Inválido", "Ingrese un período de control válido.")
            return
        self.config.control_period_us = int(
            self.control_period_us.text()
        )

        # Período de telemetría
        if not self.telemetry_period_ms.hasAcceptableInput():
            QMessageBox.warning(self, "Período de Telemetría Inválido", "Ingrese un período de telemetría válido.")
            return
        self.config.telemetry_period_ms = int(
            self.telemetry_period_ms.text()
        )

        # Offset angular del sensor AS5600
        if not self.offset_AS5600.hasAcceptableInput():
            QMessageBox.warning(self, "Offset Del Sensor Invalido", "Valores permitidos: 0.0 - 360.00 grados")
            return
        self.config.offset_AS5600 = float(
            self.offset_AS5600.text()
        )

        # Envío del modelo de configuración completo al microcontrolador
        self.connection_manager.send_model(
            self.config
        )

        print(
            self.config.to_json()  # Depuración: muestra en consola el JSON enviado
        )


    def update_connecting_status(self, connecting):
        """
        Actualiza la interfaz mientras se realiza (o cancela) un intento de
        conexión TCP.

        Mientras se conecta, bloquea el cambio de modo, muestra el estado
        "Conectando..." en amarillo y convierte el botón TCP en "Cancelar".
        Si el intento termina sin lograr conexión, restablece los controles
        al estado de desconectado.

        Args:
            connecting (bool): True si hay un intento de conexión en curso,
                False si terminó (con o sin éxito).
        """
        # print(
        #     f"TCP connecting_changed: {connecting}"  # Depuración
        # )

        # Se bloquea el cambio de modo (Serial/Red) mientras dura el intento de conexión
        self.serial_radio.setEnabled(
            not connecting
        )

        self.network_radio.setEnabled(
            not connecting
        )

        if connecting:

            set_status(
                self.connection_status,
                "● Conectando...",
                STATUS_YELLOW
            )

            self.TCP_boton.setText("Cancelar")  # Permite abortar el intento antes de que expire el timeout

            self.TCP_Equipo.setEnabled(False)

        elif not self.connection_manager.connected:  # El intento terminó sin conexión (fallo, timeout o cancelación)

            set_status(
                self.connection_status,
                "● Desconectado",
                STATUS_RED
            )

            self.TCP_boton.setText("Conectar")

            self.TCP_Equipo.setEnabled(True)
        
