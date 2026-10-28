#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
namespace PendulumNetwork {
  using MessageHandler = void (*)(JsonDocument&);
  using DisconnectHandler = void (*)();
  void begin();
  void poll(MessageHandler handler, DisconnectHandler onDisconnect);
  bool connected();
  void send(JsonDocument& document);
  void closeClient();
}
