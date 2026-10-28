MODO AP - PRUEBA SIN MOTOR ENERGIZADO

1. Abrir ESP32_InvertedPendulum_AP.ino con los .h/.cpp en la misma carpeta.
2. Editar DEVICE_NUMBER y AP_PASSWORD en NetworkConfig.h.
3. Cargar sketch. Monitor serial: SSID Pendulo_01, IP 192.168.4.1, TCP 5000.
4. En Windows, conectarse a la red Pendulo_01 con la clave elegida.
5. En Python network_config.py: NETWORK_BASE = "192.168.4." y TCP_PORT = 5000.
   IMPORTANTE: en AP el numero de equipo NO es el ultimo octeto de IP.
   Para todos los equipos en redes AP independientes la IP es 192.168.4.1.
   Cambiar la GUI para que el numero sirva como instruccion/SSID, y build_device_ip
   devuelva siempre 192.168.4.1.
6. Conectar por TCP y probar {"type":"command","command":"sensor_status"}.
7. No habilitar PID ni motor mientras se verifica la red.

Nota: WiFi SoftAP en ESP32 suele desconectar a la PC de Internet si no hay otra interfaz.
Nota: este firmware permite 1 cliente TCP y corta movimiento al desconectarse.
Nota: el timeout TCP de 30 s es un criterio de inactividad, NO un watchdog de control
      para uso con carro; antes de control real hace falta watchdog mas corto.
