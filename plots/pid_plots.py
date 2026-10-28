"""
Módulo de gráficas para la pestaña de control PID.

Define la clase PIDPlots, encargada de mostrar en tiempo real las gráficas
de "Ángulo" y "Esfuerzo de Control" correspondientes al controlador PID
(usadas en ui/pid_tab.py).
"""

from PySide6.QtWidgets import (
    QWidget,
    QGridLayout
)

from plots.live_plot import LivePlot  # Widget base reutilizable para graficar una variable en tiempo real


class PIDPlots(QWidget):
    """
    Contenedor de las gráficas del controlador PID.

    Agrupa dos instancias de LivePlot en una cuadrícula vertical:
        - Ángulo del péndulo (grados).
        - Esfuerzo de control (steps/s).
    """

    def __init__(self):
        """Inicializa el widget y construye las gráficas."""
        super().__init__()

        self.setup_ui()

    def setup_ui(self):
        """
        Crea las gráficas de ángulo y esfuerzo de control, y las organiza
        una debajo de la otra dentro de una cuadrícula (QGridLayout).
        """
        layout = QGridLayout()

        self.angle_plot = LivePlot(
            "Ángulo",
            "grados"
        )

        self.control_plot = LivePlot(
            "Esfuerzo de Control",
            "steps/s"
        )

        layout.addWidget(
            self.angle_plot,
            0,  # fila
            0   # columna
        )

        layout.addWidget(
            self.control_plot,
            1,
            0
        )

        self.setLayout(
            layout
        )

    def update_plots(
        self,
        angle,
        control_effort
    ):
        """
        Actualiza ambas gráficas con los valores más recientes.

        Args:
            angle (float): Ángulo actual del péndulo, en grados.
            control_effort (float): Esfuerzo de control actual (velocidad de control en steps/s).
        """
        self.angle_plot.update(
            angle
        )

        self.control_plot.update(
            control_effort
        )