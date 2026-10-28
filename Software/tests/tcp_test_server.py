"""
Test: Conexion esp32.

Recibe la solicitud de conexion mediante protocolo TCP y gestiona la conexion. Devuelve una respuesta de conexion  
Nota: Este documento se debe ejecutar en una terminal diferente al programa de la interfaz
"""


import socket
import json

HOST = "127.0.0.1"
PORT = 5000


def main():

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    ) as server:

        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        server.bind((HOST, PORT))
        server.listen(1)

        print(f"Servidor escuchando en {HOST}:{PORT}")

        while True:

            connection, address = server.accept()

            with connection:

                print(f"Cliente conectado: {address}")

                # makefile permite leer por líneas
                with connection.makefile("rb") as stream:

                    for line in stream:

                        try:
                            data = json.loads(
                                line.decode("utf-8")
                            )

                            print("JSON recibido:", data)

                            if not isinstance(data, dict):
                                raise ValueError(
                                    "Se esperaba un objeto JSON"
                                )

                            message_type = data.get("type")

                            if message_type == "system_config":

                                response = {
                                    "type": "ack",
                                    "for": "system_config"
                                }

                            else:

                                response = {
                                    "type": "error",
                                    "code": "INVALID_MESSAGE",
                                    "message": "Unsupported message type"
                                }

                        except (ValueError, UnicodeDecodeError) as error:

                            response = {
                                "type": "error",
                                "code": "INVALID_JSON",
                                "message": str(error)
                            }

                        payload = (
                            json.dumps(
                                response,
                                separators=(",", ":")
                            ) + "\n"
                        )

                        connection.sendall(
                            payload.encode("utf-8")
                        )

                print("Cliente desconectado")


if __name__ == "__main__":
    main()
