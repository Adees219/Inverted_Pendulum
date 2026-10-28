"""
Módulo de gráficas para la pestaña de control por retroalimentación de estado.

Define la clase StatePlots, encargada de mostrar en tiempo real las cuatro
variables de estado del péndulo (ángulo, velocidad angular, posición y
velocidad lineal), organizadas en una cuadrícula de 2x2 (usadas en
ui/state_tab.py).
"""

from PySide6.QtWidgets import (
    QWidget,
    QGridLayout
)

from plots.live_plot import LivePlot  # Widget base reutilizable para graficar una variable en tiempo real


class StatePlots(QWidget):
    """
    Contenedor de las gráficas de las variables de estado.

    Agrupa cuatro instancias de LivePlot en una cuadrícula de 2 filas x 2
    columnas:
        - Ángulo (grados)
        - Velocidad angular (grados/s)
        - Posición (mm)
        - Velocidad lineal (mm/s)
    """

    def __init__(self):
        """Inicializa el widget y construye las cuatro gráficas."""
        super().__init__()

        self.setup_ui()

    def setup_ui(self):
        """
        Crea las gráficas de ángulo, velocidad angular, posición y velocidad
        lineal, y las organiza en una cuadrícula de 2x2 (QGridLayout).
        """
        layout = QGridLayout()

        # Se crean las cuatro gráficas, una por cada variable de estado

        self.angle_plot = LivePlot(
            "Ángulo",
            "grados"
        )

        self.angular_plot = LivePlot(
            "Velocidad angular",
            "grados/s"
        )

        self.position_plot = LivePlot(
            "Posición",
            "mm"
        )

        self.linear_plot = LivePlot(
            "Velocidad lineal",
            "mm/s"
        )

        # Se agregan al layout en una cuadrícula 2x2:
        #   [ángulo]           [vel. angular]
        #   [posición]         [vel. lineal]

        layout.addWidget(
            self.angle_plot,
            0,  # fila
            0   # columna
        )

        layout.addWidget(
            self.angular_plot,
            0,
            1
        )

        layout.addWidget(
            self.position_plot,
            1,
            0
        )

        layout.addWidget(
            self.linear_plot,
            1,
            1
        )

        self.setLayout(layout)

    def update_plots(self, state):
        """
        Actualiza las cuatro gráficas con los valores más recientes del
        modelo de estado.

        Args:
            state (StateModel): Modelo con los valores actuales de angle,
                angular_velocity, position y linear_velocity.
        """
        self.angle_plot.update(
            state.angle
        )

        self.angular_plot.update(
            state.angular_velocity
        )

        self.position_plot.update(
            state.position
        )

        self.linear_plot.update(
            state.linear_velocity
        )