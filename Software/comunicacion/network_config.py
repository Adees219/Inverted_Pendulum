# ==========================================================
# CONFIGURACIÓN DE RED DEL LABORATORIO
# ==========================================================

NETWORK_BASE = "192.168.4."

TCP_PORT = 5000

TCP_CONNECT_TIMEOUT = 3.0

TCP_READ_TIMEOUT = 0.1


def build_device_ip(device_number: int) -> str:

    if not 1 <= device_number <= 254:
        raise ValueError(
            "El número de equipo debe estar entre 1 y 254"
        )

    #return f"{NETWORK_BASE}{device_number}" Solo funcional con direcciones dinamicas y empleando STA
    return "192.168.4.1" #IP fija
                        #ahora el numero del equipo en "config_tab" sirve para indicar la red a la que se conecta (identificable mediante SSID)