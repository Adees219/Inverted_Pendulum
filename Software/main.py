"""
Universidad del Valle de Guatemala
Autor: Anderson Daniel Eduardo Escobar Sandoval - 21712
Proyecto de graduación: Acondicionamiento de un sistema de péndulo invertido

Módulo principal de la interfaz gráfica. Se encarga de inicializar la
aplicación Qt y lanzar la ventana principal del sistema.

Documentación de referencia:
    - Qt Widgets: https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/index.html
    - Funciones Qt: https://doc.qt.io/qt-6/functions.html
"""

import sys  # Módulo estándar para interactuar con el entorno de ejecución (argumentos, salida del programa, etc.)

from PySide6.QtWidgets import QApplication  # Motor principal de la interfaz gráfica (gestiona ventanas, eventos, widgets)
from ui.main_window import MainWindow       # Ventana principal personalizada, definida en ui/main_window.py


def main() -> None:
    """
    Punto de entrada de la aplicación.

    Crea la instancia de QApplication, inicializa la ventana principal
    y arranca el bucle de eventos de Qt hasta que la aplicación se cierre.
    """
    app = QApplication(sys.argv)  # Administra el ciclo de vida y la configuración global de la app (recibe argumentos de consola)

    window = MainWindow()  # Instancia la ventana principal definida en ui/main_window.py
    window.show()          # Hace visible la ventana en pantalla

    # app.exec() inicia el bucle de eventos de Qt (escucha clics, teclas, señales, etc.)
    # y retorna un código de salida (0 = éxito, distinto de 0 = error) cuando el bucle termina.
    # sys.exit() propaga ese código al sistema operativo para un cierre correcto del proceso.
    sys.exit(app.exec())


if __name__ == "__main__":
    main()