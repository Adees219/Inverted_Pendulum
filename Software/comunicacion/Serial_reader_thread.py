"""
Hilo de lectura continua del puerto serial.

Define la clase SerialReaderThread, encargada de ejecutar en segundo plano
(sin bloquear la interfaz gráfica) la lectura periódica de datos entrantes
por el puerto serial, delegando cada lectura al SerialManager.
"""

from PySide6.QtCore import (
    QThread
)

import time


class SerialReaderThread(QThread):
    """
    Hilo dedicado a leer continuamente el puerto serial.

    Mientras está activo, invoca repetidamente read_once() del
    SerialManager recibido, permitiendo que la recepción de datos ocurra
    en paralelo a la interfaz gráfica (evitando que esta se congele
    esperando datos del microcontrolador).
    """

    def __init__(self, serial_manager):
        """
        Args:
            serial_manager (SerialManager): Gestor de conexión serial del
                cual se leerán los datos en cada iteración del hilo.
        """
        super().__init__()

        self.serial_manager = serial_manager

        self.running = False  # Bandera que controla si el ciclo de lectura debe seguir ejecutándose

    def run(self):
        """
        Punto de entrada del hilo (se ejecuta automáticamente al llamar a
        start()). Lee datos del puerto serial en un ciclo continuo hasta
        que self.running se establezca en False.
        """
        self.running = True

        while self.running:

            self.serial_manager.read_once()  # Intenta leer un paquete de datos disponible en el puerto

            time.sleep(0.001)  # Pequeña pausa (1 ms) para evitar saturar el CPU con lecturas constantes

    def stop(self):
        """
        Detiene el ciclo de lectura y espera a que el hilo finalice
        correctamente antes de continuar (evita cerrar la aplicación con
        el hilo aún en ejecución).
        """
        self.running = False

        self.wait()  # Bloquea hasta que run() termine su iteración actual y el hilo finalice