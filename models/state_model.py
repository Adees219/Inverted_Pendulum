"""
Modelo de las variables de estado del péndulo.

Define la clase StateModel, encargada de almacenar los valores actuales
de las cuatro variables de estado del sistema (ángulo, velocidad angular,
posición y velocidad lineal), recibidas desde el microcontrolador y
utilizadas tanto en la pestaña de control por retroalimentación de estado
(ui/state_tab.py) como en sus gráficas (plots/state_plots.py).
"""


class StateModel:
    """
    Modelo de datos para las variables de estado del péndulo.

    A diferencia de ConfigModel y PIDModel, esta clase no se envía al
    microcontrolador (no implementa to_dict/to_json); en su lugar, se
    actualiza con los datos que el microcontrolador envía hacia la
    aplicación (ver MainWindow.process_received_data).
    """

    def __init__(self):
        """Inicializa todas las variables de estado en cero."""

        self.angle = 0.0  # Ángulo del péndulo, en grados (°)

        self.angular_velocity = 0.0  # Velocidad angular del péndulo, en grados/segundo (°/s)

        self.position = 0.0  # Posición del carro/base, en milímetros (mm)

        self.linear_velocity = 0.0  # Velocidad lineal del carro/base, en milímetros/segundo (mm/s)
    def clear(self):
        self.angle = None
        self.angular_velocity = None
        self.position = None
        self.linear_velocity = None

    def update_from_telemetry(self, message):
        import math
        mapping = {
            "angle": "angle_deg",
            "angular_velocity": "angular_velocity_deg_s",
            "position": "position_mm",
            "linear_velocity": "linear_velocity_mm_s",
        }
        for attr, key in mapping.items():
            value = message.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                setattr(self, attr, None)
                continue
            value = float(value)
            setattr(self, attr, value if math.isfinite(value) else None)
