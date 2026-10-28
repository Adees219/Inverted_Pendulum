#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

// Transporte serial JSON por lineas. El dispatcher de comandos permanece
// en el .ino para no introducir dependencias del motor/control en Protocol.
namespace Protocol {
    using MessageHandler = void (*)(JsonDocument&);

    void resetSerialBuffer();
    void setTcpReplyContext(bool active);
    void sendTelemetry(JsonDocument& document);
    void pollSerial(MessageHandler handler);

    void sendJson(JsonDocument& document);
    void sendAck(const char* what, const char* command = nullptr);
    void sendError(const char* code, const char* message);
}
