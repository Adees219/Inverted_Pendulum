"""
Gestor de comunicación por red (TCP/IP).

Define la clase TCPManager, encargada de manejar la conexión, desconexión,
envío y recepción de datos con el microcontrolador a través de un socket
TCP (QTcpSocket de Qt), como alternativa al puerto serial.

Expone la misma interfaz que SerialManager (connect/disconnect/send/read_once
y las señales connection_changed, connection_error y data_received), de modo
que ConnectionManager pueda intercambiar ambos gestores sin cambiar su lógica.
Además agrega la señal connecting_changed, útil para indicar en la interfaz
que un intento de conexión está en curso.

Protocolo de mensajes: cada mensaje es un objeto JSON en una sola línea,
delimitado por un salto de línea ("\\n").
"""

import json

from PySide6.QtCore import (
    QObject,
    Signal,
    QTimer  # Temporizador usado para limitar el tiempo de espera de la conexión
)

from PySide6.QtNetwork import (
    QTcpSocket,       # Socket TCP asíncrono de Qt (no bloquea la interfaz gráfica)
    QAbstractSocket   # Clase base que define los estados del socket (Unconnected, Connecting, Connected, etc.)
)

from comunicacion.network_config import (
    TCP_PORT,             # Puerto TCP en el que escucha el microcontrolador
    TCP_CONNECT_TIMEOUT   # Tiempo máximo de espera para establecer la conexión (en segundos)
)


class TCPManager(QObject):
    """
    Gestiona la conexión y comunicación por red (TCP/IP) con el
    microcontrolador.

    Utiliza un QTcpSocket de forma asíncrona: las operaciones de conexión y
    lectura no bloquean la interfaz, y cada evento (conexión establecida,
    desconexión, datos disponibles, error) se maneja mediante señales/slots.
    """

    connection_changed = Signal(bool)  # Señal emitida cuando cambia el estado de conexión (True = conectado)
    connection_error = Signal(str)     # Señal emitida cuando ocurre un error, con el mensaje como texto
    data_received = Signal(dict)       # Señal emitida cada vez que se recibe y parsea un mensaje JSON válido
    connecting_changed = Signal(bool)  # Señal emitida al iniciar (True) o finalizar (False) un intento de conexión

    def __init__(self):
        """
        Inicializa el socket TCP, el temporizador de timeout, el buffer de
        recepción y conecta las señales del socket con sus respectivos manejadores.
        """
        super().__init__()

        self.connected = False  # Bandera que indica si actualmente hay una conexión TCP activa

        self.socket = QTcpSocket(self)  # Socket TCP (se pasa "self" como padre para que Qt gestione su ciclo de vida)

        # Temporizador de un solo disparo: si la conexión no se establece antes de que
        # expire, se cancela el intento y se notifica el error (ver on_connection_timeout)
        self.connect_timer = QTimer(self)

        self.connect_timer.setSingleShot(True)

        self.connect_timer.timeout.connect(
            self.on_connection_timeout
        )

        # Buffer para reconstruir mensajes JSON: TCP es un flujo continuo de bytes, por lo que un
        # mensaje puede llegar fragmentado o varios mensajes pueden llegar juntos en una misma lectura
        self.receive_buffer = bytearray()

        # Heartbeat TCP: independiente de la telemetria y del control motor.
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.setInterval(2000)
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)

        # ==========================================================
        # Señales del socket
        # ==========================================================

        self.socket.connected.connect(  # El socket logró establecer la conexión
            self.on_connected
        )

        self.socket.disconnected.connect(  # El socket se desconectó (por el usuario o por el equipo remoto)
            self.on_disconnected
        )

        self.socket.readyRead.connect(  # Hay nuevos datos disponibles para leer en el socket
            self.read_once
        )

        self.socket.errorOccurred.connect(  # Ocurrió un error en el socket (host no encontrado, conexión rechazada, etc.)
            self.on_error
        )

    # ==============================================================
    # Conexión
    # ==============================================================

    def connect_network(self, ip):
        """
        Inicia la conexión TCP con el equipo indicado.

        La conexión es asíncrona: este método retorna de inmediato y el
        resultado se notifica mediante las señales connection_changed (éxito)
        o connection_error (fallo). Si el socket no está en estado
        desconectado (ya conectando o conectado), la llamada se ignora.

        Args:
            ip (str): Dirección IP del equipo al que se desea conectar.
        """
        if self.socket.state() != QAbstractSocket.UnconnectedState:  # Evita iniciar una segunda conexión simultánea
            return

        self.receive_buffer.clear()  # Descarta datos residuales de una conexión anterior

        # print("TCPManager: iniciando conexión")  # Depuración

        self.connecting_changed.emit(True)  # Notifica a la interfaz que se está intentando conectar

        self.connect_timer.start(
            int(TCP_CONNECT_TIMEOUT * 1000)  # Conversión de segundos a milisegundos
        )

        self.socket.connectToHost(
            ip,
            TCP_PORT
        )

    def on_connected(self):
        """
        Manejador de la señal connected del socket: se ejecuta cuando la
        conexión TCP se establece correctamente.
        """
        self.connect_timer.stop()  # La conexión fue exitosa, ya no se necesita el timeout

        self.connected = True
        self.heartbeat_timer.start()

        self.connecting_changed.emit(False)  # Finaliza el estado "conectando"

        self.connection_changed.emit(True)

    # ==============================================================
    # Desconexión
    # ==============================================================

    def disconnect_network(self):
        """
        Cierra la conexión TCP actual o cancela un intento de conexión en curso.

        - Si el socket ya está desconectado, no hace nada.
        - Si aún está conectando, aborta el intento de inmediato.
        - Si está conectado, solicita un cierre ordenado; la notificación
          final llegará a través de on_disconnected.
        """
        self.connect_timer.stop()

        if self.socket.state() == QAbstractSocket.UnconnectedState:  # No hay nada que desconectar
            return

        if self.socket.state() == QAbstractSocket.ConnectingState:  # Cancelación de un intento en curso

            self.socket.abort()  # Cierra el socket inmediatamente, sin esperar el cierre ordenado

            self.connecting_changed.emit(False)

            return

        self.socket.disconnectFromHost()  # Cierre ordenado: envía lo pendiente y luego cierra la conexión

    def on_disconnected(self):
        """
        Manejador de la señal disconnected del socket: se ejecuta cuando la
        conexión se cierra, ya sea por el usuario o por el equipo remoto.
        Restablece el estado interno y notifica a la interfaz.
        """
        self.connect_timer.stop()

        self.connected = False
        self.heartbeat_timer.stop()

        self.receive_buffer.clear()  # Evita que datos incompletos de esta sesión contaminen la siguiente

        self.connecting_changed.emit(False)

        self.connection_changed.emit(False)

    # ==============================================================
    # Envío
    # ==============================================================

    def send(self, data):
        """
        Envía una cadena de texto (normalmente JSON) al microcontrolador
        a través del socket TCP.

        Si no hay conexión activa, emite connection_error en lugar de enviar.

        Args:
            data (str): Datos a enviar. Se normaliza para terminar en un único
                salto de línea ("\\n"), que actúa como delimitador de mensaje.
        """
        if not self.connected:

            self.connection_error.emit(
                "No existe conexión TCP activa."
            )

            return

        try:

            message = (
                data.rstrip("\r\n") + "\n"  # Elimina saltos de línea sobrantes y agrega exactamente uno al final
            )

            self.socket.write(
                message.encode("utf-8")  # El socket trabaja con bytes, por lo que se codifica el texto a UTF-8
            )

        except (TypeError, UnicodeError) as error:

            self.connection_error.emit(
                str(error)
            )

    # ==============================================================
    # Recepción
    # ==============================================================

    def send_heartbeat(self):
        """Mantiene activa la sesion TCP; no ordena movimiento."""
        if self.connected:
            self.send('{"type":"heartbeat"}')

    def read_once(self):
        """
        Lee los datos disponibles en el socket, reconstruye los mensajes
        completos (delimitados por "\\n") y emite data_received por cada
        mensaje JSON válido.

        Se ejecuta automáticamente cada vez que el socket recibe datos
        (señal readyRead). Mantiene el mismo nombre que en SerialManager
        para conservar una interfaz común entre ambos gestores.

        Los mensajes inválidos (JSON mal formado, codificación incorrecta o
        que no sean un objeto JSON) se descartan y se notifican mediante
        connection_error.
        """
        self.receive_buffer.extend(
            bytes(self.socket.readAll())  # Agrega al buffer todo lo recibido hasta el momento
        )
        

        # Se procesan todos los mensajes completos presentes en el buffer; si el último
        # quedó incompleto (sin "\n"), permanece en el buffer hasta la siguiente lectura
        while b"\n" in self.receive_buffer:

            line, _, remaining = (
                self.receive_buffer.partition(b"\n")  # Separa el primer mensaje completo del resto del buffer
            )

            self.receive_buffer = bytearray(
                remaining  # El buffer conserva únicamente lo que aún no se ha procesado
            )

            line = line.strip()

            if not line:  # Línea vacía: se ignora
                continue

            try:

                data = json.loads(
                    line.decode("utf-8")
                )

                if not isinstance(data, dict):  # Se exige que el mensaje sea un objeto JSON ({...}), no una lista o valor suelto
                    raise ValueError(
                        "El mensaje JSON debe ser un objeto."
                    )

                self.data_received.emit(
                    data
                )

            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
                ValueError
            ) as error:

                self.connection_error.emit(
                    f"Mensaje TCP inválido: {error}"
                )

    # ==============================================================
    # Eventos
    # ==============================================================

    def on_error(self, error):
        """
        Manejador de la señal errorOccurred del socket: se ejecuta ante
        cualquier error de red (host inaccesible, conexión rechazada, etc.).

        Args:
            error (QAbstractSocket.SocketError): Código del error ocurrido
                (el mensaje legible se obtiene con socket.errorString()).
        """
        self.connect_timer.stop()

        self.connecting_changed.emit(False)

        self.connection_error.emit(
            self.socket.errorString()  # Descripción del error en texto legible
        )

    # ==============================================================
    # Time out
    # ==============================================================

    def on_connection_timeout(self):
        """
        Manejador del temporizador de conexión: se ejecuta si transcurre el
        tiempo máximo (TCP_CONNECT_TIMEOUT) sin lograr establecer la conexión.
        Cancela el intento y notifica el error a la interfaz.
        """
        if self.socket.state() == QAbstractSocket.ConnectedState:  # La conexión se logró justo a tiempo: no hay nada que cancelar
            return

        self.socket.abort()  # Cancela el intento de conexión pendiente

        self.connected = False

        self.connecting_changed.emit(False)

        self.connection_error.emit(
            "Tiempo de espera agotado. "
            "No se pudo establecer conexión con el equipo."
        )