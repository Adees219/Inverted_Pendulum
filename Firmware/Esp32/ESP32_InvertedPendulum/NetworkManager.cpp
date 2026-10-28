#include "NetworkManager.h"
#include "NetworkConfig.h"
#include "HardwareConfig.h"

namespace {
  WiFiServer server(TCP_PORT);
  WiFiClient client;
  char buffer[MAX_LINE];
  size_t length = 0;
  bool overflow = false;
  uint32_t lastActivity = 0;
  void clearBuffer() { length = 0; overflow = false; }
}
namespace PendulumNetwork {
  void begin() {
    char ssid[32];
    snprintf(ssid, sizeof(ssid), "Pendulo_%02u", (unsigned)DEVICE_NUMBER);
    WiFi.mode(WIFI_AP);
    WiFi.softAPConfig(IPAddress(192,168,4,1), IPAddress(192,168,4,1), IPAddress(255,255,255,0));
    if (!WiFi.softAP(ssid, AP_PASSWORD, AP_CHANNEL, false, 1)) {
      Serial.println("[AP] ERROR al iniciar red");
      return;
    }
    server.begin();
    Serial.print("[AP] SSID: "); Serial.println(ssid);
    Serial.print("[AP] IP: "); Serial.println(WiFi.softAPIP());
    Serial.print("[AP] TCP puerto: "); Serial.println(TCP_PORT);
  }
  bool connected() { return client && client.connected(); }
  void closeClient() { if (client) client.stop(); clearBuffer(); }
  void send(JsonDocument& document)
{
    if (!client || !client.connected())
    {
        // Serial.println(
        //     "[TCP TX] No hay cliente conectado"
        // );
         return;
    }

    // Convertir el documento a una linea JSON
    String payload;
    serializeJson(document, payload);

    payload += '\n';

    // Enviar el mensaje completo
    size_t written = client.write(
        reinterpret_cast<const uint8_t*>(payload.c_str()),
        payload.length()
    );

    // Serial.print("[TCP TX] Bytes esperados: ");
    // Serial.println(payload.length());

    // Serial.print("[TCP TX] Bytes escritos: ");
    // Serial.println(written);

    // Serial.print("[TCP TX] Contenido: ");
    // Serial.print(payload);
}
  void poll(MessageHandler handler, DisconnectHandler onDisconnect) {
    if (client && !client.connected()) {
      closeClient();
      if (onDisconnect) onDisconnect();
    }
    WiFiClient incoming = server.accept();
    if (incoming) {
      if (!connected()) {
        client = incoming;
        client.setNoDelay(true);
        lastActivity = millis();
        clearBuffer();
        Serial.println("[AP] Cliente TCP conectado");
      } else incoming.stop(); // un solo cliente de control
    }
    if (!connected()) return;
    if ((uint32_t)(millis() - lastActivity) > TCP_IDLE_TIMEOUT_MS) {
      closeClient();
      if (onDisconnect) onDisconnect();
      Serial.println("[AP] Cliente TCP inactivo; desconectado");
      return;
    }
    uint8_t budget = 32;
    while (client.available() && budget--) {
      char c = (char)client.read();
      lastActivity = millis();
      if (c == '\r') continue;
      if (c == '\n') {
        if (overflow) {
          JsonDocument err; err["type"]="error"; err["code"]="INVALID_MESSAGE";
          err["message"]="Message too long"; send(err);
        } else if (length) {
          buffer[length] = '\0';
          JsonDocument doc;
          DeserializationError err = deserializeJson(doc, buffer);
          if (err) {
            JsonDocument out; out["type"]="error"; out["code"]="INVALID_JSON";
            out["message"]="JSON deserialization failed"; send(out);
          } else if (doc["type"].is<const char*>() &&
                     strcmp(doc["type"].as<const char*>(), "heartbeat") == 0) {
              JsonDocument pong;
              pong["type"] = "heartbeat";
              pong["status"] = "ok";
              send(pong);
            } else if (handler) handler(doc);
        }
        clearBuffer(); continue;
      }
      if (overflow) continue;
      if (length >= MAX_LINE - 1) { overflow = true; continue; }
      buffer[length++] = c;
    }
  }
}
