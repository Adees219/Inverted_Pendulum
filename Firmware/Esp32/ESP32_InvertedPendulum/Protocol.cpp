#include "Protocol.h"
#include "HardwareConfig.h"
#include "NetworkManager.h"

namespace {
    bool tcpReplyContext = false;
    char lineBuffer[MAX_LINE];
    size_t lineLength = 0;
    bool lineOverflow = false;

    void processLine(const char* text, Protocol::MessageHandler handler) {
        JsonDocument document;
        DeserializationError error = deserializeJson(document, text);
        if (error) {
            Protocol::sendError("INVALID_JSON", "JSON deserialization failed");
            return;
        }
        if (handler != nullptr) handler(document);
    }
}

namespace Protocol {
    void setTcpReplyContext(bool active) { tcpReplyContext = active; }

    void sendTelemetry(JsonDocument& document) {
        serializeJson(document, Serial); Serial.println();
        PendulumNetwork::send(document);
    }

    void resetSerialBuffer() {
        lineLength = 0;
        lineOverflow = false;
    }

    void sendJson(JsonDocument& document) {
        Serial.print("[PROTO] Respuesta por: ");

        Serial.println(
            tcpReplyContext ? "TCP" : "SERIAL"
        );
        if (tcpReplyContext) PendulumNetwork::send(document);
        else { serializeJson(document, Serial); Serial.println(); }
    }

    void sendAck(const char* what, const char* command) {
        JsonDocument document;
        document["type"] = "ack";
        document["for"] = what;
        if (command) document["command"] = command;
        sendJson(document);
    }

    void sendError(const char* code, const char* message) {
        JsonDocument document;
        document["type"] = "error";
        document["code"] = code;
        document["message"] = message;
        sendJson(document);
    }

    void pollSerial(MessageHandler handler) {
        // Mantener el presupuesto previo para no bloquear la generacion STEP.
        uint8_t budget = 32;
        while (Serial.available() && budget--) {
            const char c = (char)Serial.read();
            if (c == '\r') continue;
            if (c == '\n') {
                if (lineOverflow) {
                    sendError("INVALID_MESSAGE", "Message too long");
                } else if (lineLength) {
                    lineBuffer[lineLength] = '\0';
                    processLine(lineBuffer, handler);
                }
                resetSerialBuffer();
                continue;
            }
            if (lineOverflow) continue;
            if (lineLength >= MAX_LINE - 1) {
                lineOverflow = true;
                continue;
            }
            lineBuffer[lineLength++] = c;
        }
    }
}
