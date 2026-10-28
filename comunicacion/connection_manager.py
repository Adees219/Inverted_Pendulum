"""
Gestor central de conexión con el hardware.

Define la clase ConnectionManager, encargada de actuar como capa
intermedia entre la interfaz gráfica y los dos métodos de comunicación
disponibles (Serial y TCP/IP). Unifica el envío/recepción de datos bajo
una misma interfaz, sin que el resto de la aplicación necesite saber si
la conexión activa es serial o de red.
"""

from PySide6.QtCore import (
    QObject,
    Signal
)

from comunicacion.serial_manager import (  # Gestor del método de conexión Serial
    SerialManager
)

from comunicacion.tcp_manager import (  # Gestor del método de conexión TCP/IP
    TCPManager
)

from comunicacion.Serial_reader_thread import (
    SerialReaderThread  # Hilo dedicado a leer datos entrantes por el puerto serial sin bloquear la interfaz
)


class ConnectionManager(QObject):
    """
    Punto único de acceso a la comunicación con el microcontrolador.

    Decide, según el modo activo (Serial o Red), a cuál de los dos
    gestores (SerialManager o TCPManager) delegar cada operación de
    conexión, desconexión, envío y lectura de datos. Además, reenvía
    (a través de señales propias) los eventos de conexión y los datos
    recibidos, sin importar el método de comunicación utilizado.
    """

    connection_changed = Signal(bool)  # Señal emitida cuando cambia el estado de conexión (True = conectado)
    data_received = Signal(dict)       # Señal emitida cada vez que llegan nuevos datos del microcontrolador
    connecting_changed = Signal(bool)  # Señal emitida al iniciar (True) o finalizar (False) un intento de conexión TCP

    # Constantes que identifican el modo de conexión
    SERIAL = "serial"
    NETWORK = "network"

    def __init__(self):
        """
        Inicializa los gestores de comunicación (Serial y TCP), el hilo de
        lectura serial, y conecta sus señales internas a las señales
        públicas de ConnectionManager.
        """
        super().__init__()

        self.serial_manager = (  # Instancia del gestor de comunicación serial
            SerialManager()
        )

        self.serial_thread = SerialReaderThread(  # Hilo que lee continuamente el puerto serial en segundo plano
            self.serial_manager
        )

        self.tcp_manager = (  # Instancia del gestor de comunicación por red (TCP/IP)
            TCPManager()
        )

        # Se reenvían los cambios de estado de conexión de ambos gestores hacia la señal pública
        self.serial_manager.connection_changed.connect(
            self.connection_changed.emit
        )

        self.tcp_manager.connection_changed.connect(
            self.connection_changed.emit
        )
        
        # Se reenvía el estado "conectando" del gestor TCP hacia la señal pública. Se usa un método
        # intermedio (forward_connecting_status) en lugar de conectar directamente a .emit, lo que
        # permite depurar cada evento. Alternativa directa, sin depuración:
        # self.tcp_manager.connecting_changed.connect(
        #     self.connecting_changed.emit
        # )
        self.tcp_manager.connecting_changed.connect(
            self.forward_connecting_status
        )

        self.current_mode = self.SERIAL  # Modo de conexión predeterminado al iniciar la aplicación

        # Se reenvían los datos recibidos de ambos gestores hacia la señal pública
        self.serial_manager.data_received.connect(
            self.data_received.emit
        )

        self.tcp_manager.data_received.connect(
            self.data_received.emit
        )

    def set_mode(self, mode: str):
        """
        Define el método de conexión activo (Serial o Red).

        Args:
            mode (str): Uno de los valores ConnectionManager.SERIAL o
                ConnectionManager.NETWORK.
        """
        self.current_mode = mode

    def connect(self, target):
        """
        Establece la conexión con el microcontrolador usando el modo actual.

        Si el modo es Serial, conecta el puerto indicado y, de tener éxito,
        inicia el hilo de lectura. Si el modo es Red, se conecta a la
        dirección IP/equipo indicado.

        Args:
            target (str): Puerto COM (modo Serial) o dirección IP (modo Red)
                al que se desea conectar.
        """
        if self.current_mode == self.SERIAL:

            self.serial_manager.connect_port(
                target
            )

            if self.serial_manager.connected:

                self.serial_thread.start()  # Inicia la lectura continua del puerto solo si la conexión fue exitosa

        else:

            self.tcp_manager.connect_network(
                target
            )

    def disconnect(self):
        """
        Cierra la conexión activa según el modo actual.

        En modo Serial, detiene primero el hilo de lectura (si está
        corriendo) antes de cerrar el puerto, para evitar accesos
        concurrentes al recurso ya liberado.
        """
        if self.current_mode == self.SERIAL:

            if self.serial_thread.isRunning():

                self.serial_thread.stop()


            self.serial_manager.disconnect_port()

  
        else:

            self.tcp_manager.disconnect_network()

    def get_available_ports(self):
        """
        Obtiene la lista de puertos COM disponibles en el equipo.

        Returns:
            list[str]: Nombres de los puertos serie detectados.
        """
        return (
            self.serial_manager
            .get_available_ports()
        )

    @property  # Permite acceder a "connected" como si fuera un atributo (sin paréntesis), en vez de un método
    def connected(self):
        """
        Indica si existe una conexión activa en el modo actualmente seleccionado.

        Returns:
            bool: True si hay conexión activa (Serial o Red, según el modo), False si no.
        """
        if self.current_mode == self.SERIAL:

            return (
                self.serial_manager.connected
            )

        return (
            self.tcp_manager.connected
        )

    def send(self, data):
        """
        Envía datos ya serializados (JSON) al microcontrolador, usando el
        gestor correspondiente al modo de conexión actual.

        Args:
            data (str): Cadena de datos (JSON) a enviar.
        """
        if self.current_mode == self.SERIAL:

            self.serial_manager.send(
                data
            )

        else:

            self.tcp_manager.send(
                data
            )

    def send_model(self, model):
        """
        Serializa un modelo de datos (ConfigModel, PIDModel, etc.) a JSON
        y lo envía al microcontrolador.

        Args:
            model: Instancia de un modelo que implementa el método to_json().
        """
        self.send(
            model.to_json()
        )

    def read_once(self):
        """
        Realiza una lectura puntual de datos desde el gestor correspondiente
        al modo de conexión actual (Serial o Red).
        """
        if self.current_mode == self.SERIAL:

            self.serial_manager.read_once()

        else:

            self.tcp_manager.read_once()

   
    def forward_connecting_status(self, connecting):
        """
        Reenvía hacia la señal pública connecting_changed el estado de
        "conectando" emitido por el gestor TCP, para que la interfaz pueda
        mostrar el progreso del intento de conexión.

        Args:
            connecting (bool): True si inicia un intento de conexión, False si finaliza.
        """
        # print(
        #     f"ConnectionManager recibió: {connecting}"  # Depuración
        # )

        self.connecting_changed.emit(
            connecting
        )