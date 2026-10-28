"""
Gestor de comunicación por puerto serial.

Define la clase SerialManager, encargada de detectar, conectar,
desconectar, enviar y recibir datos a través de un puerto serial (USB/UART)
con el microcontrolador, usando la librería pyserial.
"""

from PySide6.QtCore import (
    QObject,
    Signal  # Emite señales cuando ocurre un evento; junto con los "slots" reemplaza a los callbacks tradicionales
)

import json

import serial.tools.list_ports  # Permite obtener la lista de puertos disponibles en el sistema: https://pyserial.readthedocs.io/en/latest/tools.html
import serial  # Librería de comunicación serial (pyserial)


class SerialManager(QObject):
    """
    Gestiona la conexión y comunicación por puerto serial con el
    microcontrolador.

    Se encarga de listar los puertos disponibles, abrir/cerrar la conexión,
    enviar comandos en formato JSON y leer/parsear los datos entrantes,
    notificando cada evento (conexión, error, datos recibidos) mediante señales de Qt.
    """

    connection_changed = Signal(bool)  # Señal emitida cuando cambia el estado de conexión (True = conectado, False = desconectado)
    connection_error = Signal(str)     # Señal emitida cuando ocurre un error de conexión, con el mensaje de error como texto

    data_received = Signal(dict)  # Señal emitida cada vez que se recibe y parsea correctamente un paquete de datos

    def __init__(self):
        """Inicializa el gestor sin ninguna conexión activa."""
        super().__init__()

        self.connected = False  # Bandera que indica si actualmente hay un puerto serial abierto

        self.serial = None  # Referencia al objeto serial.Serial una vez establecida la conexión

    def get_available_ports(self):
        """
        Obtiene los nombres de los puertos serie disponibles en el sistema.

        Returns:
            list[str]: Lista con el nombre de dispositivo (p. ej. "COM3") de
                cada puerto detectado.
        """
        ports = []

        for port in serial.tools.list_ports.comports():

            ports.append(port.device)  # "device" contiene el nombre completo del dispositivo (p. ej. "COM3")

        return ports

    def connect_port(self, port):
        """
        Abre la conexión con el puerto serial indicado.

        Si la conexión es exitosa, actualiza el estado interno y emite
        connection_changed(True). Si falla, emite connection_changed(False)
        junto con connection_error con el detalle del problema.

        Args:
            port (str): Nombre del puerto COM al que se desea conectar.
        """
        # print(
        #     f"Conectando a {port}"  # Depuración: muestra en consola el puerto al que se intenta conectar
        # )

        try:

            self.serial = serial.Serial(
                port,
                115200,  # Velocidad de comunicación (baud rate), debe coincidir con la del microcontrolador
                timeout=1  # Tiempo máximo de espera (segundos) antes de que una lectura falle
            )

            self.connected = True

            self.connection_changed.emit(
                True
            )

        except Exception as e:

            self.connected = False

            self.connection_changed.emit(
                False
            )

            self.connection_error.emit(
                str(e)  # Mensaje de error capturado (p. ej. puerto ocupado, no encontrado, permisos, etc.)
            )

    def disconnect_port(self):
        """
        Cierra el puerto serial actualmente abierto (si existe) y notifica
        el nuevo estado de desconexión.
        """
        if self.serial:

            self.serial.close()

        self.connected = False

        self.connection_changed.emit(
            False  # Actualiza la señal: ya no hay ningún puerto conectado
        )

    def send(self, data):
        """
        Envía una cadena de texto (normalmente JSON) al microcontrolador
        a través del puerto serial.

        No hace nada si no hay una conexión activa.

        Args:
            data (str): Datos a enviar (se le agrega un salto de línea "\\n" al final).
        """
        if not self.connected:

            return

        self.serial.write(
            (data + "\n").encode("utf-8")  # Se codifica a bytes UTF-8 y se agrega salto de línea como delimitador de mensaje
        )

    def read_once(self):
        """
        Intenta leer una línea de datos desde el puerto serial y, si es un
        JSON válido, la convierte a diccionario y emite data_received.

        No hace nada si no hay una conexión activa. Si la línea recibida
        está vacía o no es JSON válido, se ignora (o se informa por consola).
        """
        if not self.connected:

            return

        line = (
            self.serial.readline().decode("utf-8").strip()  # Lee una línea, la decodifica de bytes a texto y quita espacios/saltos sobrantes
        )

        if not line:

            return  # No se recibió nada (timeout o línea vacía): se ignora este ciclo

        try:

            data = json.loads(
                line
            )

            self.data_received.emit(
                data
            )

        except json.JSONDecodeError:

            print(
                "JSON inválido"  # La línea recibida no tiene un formato JSON válido (p. ej. datos corruptos o incompletos)
            )