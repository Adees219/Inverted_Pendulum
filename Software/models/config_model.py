"""
Modelo de configuración general del sistema.

Define la clase ConfigModel, encargada de almacenar los parámetros de
configuración del sistema (amperaje, microstepping, velocidad máxima,
aceleración, períodos de control/telemetría y offset del sensor AS5600),
y de serializarlos al formato JSON esperado por el microcontrolador.
"""

import json


class ConfigModel:
    """
    Modelo de datos para la configuración general del sistema.

    Almacena los parámetros configurables desde la pestaña de Configuración
    (ui/config_tab.py) y provee métodos para convertirlos a un diccionario
    o a una cadena JSON, en el formato que espera el microcontrolador.
    """

    def __init__(self):
        """Inicializa el modelo con los valores predeterminados del sistema."""

        # Valores iniciales
        self.type = "system_config"  # Identificador del tipo de mensaje, usado por el microcontrolador para distinguirlo

        self.amperaje = 800  # Corriente del motor, en mA

        self.microstep = 16  # Nivel de microstepping del driver (TMC2209)

        self.velocidad_maxima = 32000  # Velocidad máxima permitida, en steps/s

        self.aceleracion = 150000  # Aceleración del motor, en steps/s^2

        self.control_period_us = 1000  # Período del lazo de control, en microsegundos

        self.telemetry_period_ms = 20  # Período de envío de telemetría, en milisegundos

        self.offset_AS5600 = 283.0  # Offset angular del sensor AS5600, en grados

    def to_dict(self):
        """
        Convierte los atributos del modelo a un diccionario con las claves
        (en inglés/snake_case) esperadas por el microcontrolador.

        Returns:
            dict: Configuración actual del sistema, lista para serializar.
        """
        # Formato de salida: mapea los nombres de atributo (en español) a las
        # claves del protocolo de comunicación (en inglés)
        return {
            "type": self.type,
            "current_ma": self.amperaje,
            "microsteps": self.microstep,
            "max_speed_steps_s": self.velocidad_maxima,
            "acceleration_steps_s2": self.aceleracion,
            "control_period_us": self.control_period_us,
            "telemetry_period_ms": self.telemetry_period_ms,
            "encoder_offset_deg": self.offset_AS5600
        }

    def to_json(self):
        """
        Serializa la configuración actual a una cadena JSON compacta (sin
        espacios), lista para enviarse por el medio de comunicación elegido
        (Serial o Red).

        Returns:
            str: Representación JSON de la configuración.
        """
        # JSON compacto: separadores sin espacios para reducir el tamaño del mensaje
        return json.dumps(
            self.to_dict(),
            separators=(",", ":")
        )