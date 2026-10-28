"""
Modelo de configuración del controlador PID.

Define la clase PIDModel, encargada de almacenar las ganancias (Kp, Ki, Kd)
y el modo de equilibrio (arriba/abajo) del controlador PID, y de
serializarlos al formato JSON esperado por el microcontrolador.
"""

import json


class PIDModel:
    """
    Modelo de datos para la configuración del controlador PID.

    Almacena los valores configurables desde la pestaña de Control PID
    (ui/pid_tab.py) y provee métodos para convertirlos a un diccionario
    o a una cadena JSON.
    """

    UP = "up"      # Valor constante para el modo "equilibrio arriba"
    DOWN = "down"   # Valor constante para el modo "equilibrio abajo"

    def __init__(self):
        """Inicializa el modelo con los valores predeterminados del controlador PID."""

        self.mode = self.DOWN  # Modo de equilibrio del péndulo (por defecto: abajo)

        self.kp = 900.0   # Ganancia proporcional

        self.ki = 0.001    # Ganancia integral

        self.kd = 0.001    # Ganancia derivativa

    def to_dict(self):
        """
        Convierte los atributos del modelo a un diccionario, en el formato
        esperado por el microcontrolador.

        Returns:
            dict: Configuración actual del controlador PID, lista para serializar.
        """
        return {
            "mode": self.mode,
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd
        }

    def to_json(self):
        """
        Serializa la configuración actual del PID a una cadena JSON legible
        (con indentación), lista para enviarse por el medio de comunicación
        elegido (Serial o Red).

        Returns:
            str: Representación JSON de la configuración del PID.
        """
        return json.dumps(
            self.to_dict(),
            #indent=4  # Formato legible (multilínea, con sangría de 4 espacios)
            separators=(",", ":")
        )