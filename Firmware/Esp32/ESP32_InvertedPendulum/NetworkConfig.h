#pragma once
#include <Arduino.h>
// EDITAR SOLO ESTAS CONSTANTES PARA CAMBIAR EL EQUIPO
constexpr uint8_t DEVICE_NUMBER = 2; //RED
constexpr char AP_PASSWORD[] = "PenduloLab_2"; 
constexpr uint16_t TCP_PORT = 5000;
constexpr uint8_t AP_CHANNEL = 6;
constexpr uint32_t TCP_IDLE_TIMEOUT_MS = 30000; // desconexion por inactividad, solo si hay cliente (TCA)
