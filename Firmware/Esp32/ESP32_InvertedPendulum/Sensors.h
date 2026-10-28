#pragma once

#include <Arduino.h>

// Modulo de adquisicion AS5600: no calcula estados ni controla el motor.
namespace Sensors {
    enum class Encoder : uint8_t { Pendulum, Cart };

    void begin();
    bool devicePresent(Encoder encoder);
    bool readRaw(Encoder encoder, uint16_t& raw);
    bool readStatus(Encoder encoder, uint8_t& status);
}
