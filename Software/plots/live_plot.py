"""
Widget de gráfico en tiempo real reutilizable.

Define la clase LivePlot, encargada de mostrar una curva que se va
actualizando dinámicamente a partir de un buffer de tamaño fijo. Se usa
como bloque base para construir las distintas gráficas del sistema (PID,
variables de estado, etc.), pasando solo el título y la etiqueta del eje Y.
"""

from collections import deque  # Estructura de datos tipo cola con tamaño máximo fijo (usada como buffer circular)

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout
)

import pyqtgraph as pg
import math  # Librería de graficación en tiempo real, optimizada para actualizaciones rápidas

from ui.constants.ui_constants import (
    PLOT_BUFFER_SIZE,   # Cantidad máxima de muestras que se mantienen visibles en el gráfico
    GRAPH_MIN_HEIGHT    # Altura mínima que debe tener el widget de gráfico
)


class LivePlot(QWidget):
    """
    Widget genérico de gráfico en tiempo real.

    Muestra una sola curva que se actualiza llamando a update(), conservando
    únicamente las últimas `max_samples` muestras (las más antiguas se
    descartan automáticamente al llenarse el buffer).
    """

    def __init__(
        self,
        title,
        ylabel,
        max_samples=PLOT_BUFFER_SIZE  # Muestras máximas que conserva el buffer antes de descartar las más antiguas
    ):
        """
        Args:
            title (str): Título que se muestra en la parte superior del gráfico.
            ylabel (str): Etiqueta del eje Y (unidad/variable graficada).
            max_samples (int, optional): Tamaño máximo del buffer de datos.
                Por defecto usa PLOT_BUFFER_SIZE.
        """
        super().__init__()

        self.buffer = deque(maxlen=max_samples)  # Buffer circular: al llenarse, descarta automáticamente el valor más antiguo

        self.setup_ui(title, ylabel)

    def setup_ui(self, title, ylabel):
        """
        Construye el widget de gráfico (pyqtgraph), configura sus etiquetas,
        cuadrícula y curva, y lo inserta en el layout del widget.

        Args:
            title (str): Título del gráfico.
            ylabel (str): Etiqueta del eje Y.
        """
        self.plot = pg.PlotWidget()  # Widget de pyqtgraph que renderiza el gráfico

        self.plot.setTitle(title)  # Título del gráfico

        self.plot.setLabel(  # Etiqueta del eje Y (vertical)
            "left",
            ylabel
        )

        self.plot.setLabel(  # Etiqueta del eje X (horizontal)
            "bottom",
            "Muestras"
        )

        self.plot.showGrid(  # Muestra la cuadrícula de fondo en ambos ejes
            x=True,
            y=True
        )

        self.curve = self.plot.plot(  # Crea la curva (línea) que se irá actualizando con los nuevos datos
            pen="y"  # Color de la línea: amarillo
        )

        # Agregando al layout

        self.setMinimumHeight(
            GRAPH_MIN_HEIGHT  # Evita que el gráfico se comprima demasiado al redimensionar la ventana
        )

        layout = QVBoxLayout()

        layout.addWidget(
            self.plot
        )

        self.setLayout(layout)

    def update(
            self,
            value
    ):
        """
        Agrega un nuevo valor al buffer y refresca la curva del gráfico.

        Args:
            value (float): Nueva muestra a graficar (se añade al final del buffer;
                si el buffer está lleno, se descarta automáticamente la muestra más antigua).
        """
        # NaN crea una discontinuidad en la curva sin inventar un cero.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            value = math.nan
        else:
            value = float(value)
            if not math.isfinite(value):
                value = math.nan
        self.buffer.append(value)

        self.curve.setData(
            list(self.buffer)  # pyqtgraph requiere una lista/array, por eso se convierte el deque antes de graficar
        )