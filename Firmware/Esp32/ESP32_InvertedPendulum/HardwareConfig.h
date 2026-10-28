
#pragma once

#include <Arduino.h>

// =====================================================
// COMUNICACION
// =====================================================

constexpr uint32_t SERIAL_BAUD = 115200;

// =====================================================
// MOTOR - TMC2209
// =====================================================

constexpr uint8_t STEP_PIN = 12;
constexpr uint8_t DIR_PIN  = 14;
constexpr uint8_t EN_PIN   = 15;

constexpr uint8_t TMC_TX = 26;
constexpr uint8_t TMC_RX = 27;

constexpr float R_SENSE = 0.11f;
constexpr uint8_t DRIVER_ADDR = 0;

// =====================================================
// FINALES DE CARRERA - CONTACTOS NC
// =====================================================

constexpr uint8_t LIMIT_LEFT  = 32;
constexpr uint8_t LIMIT_RIGHT = 33;

// =====================================================
// AS5600
// =====================================================

constexpr uint8_t PEND_SDA = 21;
constexpr uint8_t PEND_SCL = 22;

constexpr uint8_t CART_SDA = 18;
constexpr uint8_t CART_SCL = 19;


constexpr uint8_t AS5600_ADDR = 0x36;

// =====================================================
// PROTOCOLO
// =====================================================

constexpr size_t MAX_LINE = 512;

// =====================================================
// PERMISOS DE SEGURIDAD
// =====================================================

constexpr bool ALLOW_MOTOR_BENCH_TEST = true;
constexpr bool ALLOW_CLOSED_LOOP = false;

// =====================================================
// LIMITES DE DIAGNOSTICO
// =====================================================

constexpr float BENCH_MAX_SPEED = 100.0f;
constexpr uint32_t BENCH_TIMEOUT_MS = 3000;

// =====================================================
// MATEMATICAS
// =====================================================

constexpr float PI_F = 3.14159265358979323846f;
