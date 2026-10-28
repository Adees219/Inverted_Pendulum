
#pragma once

#include <Arduino.h>
#include <stdint.h>

// =====================================================
// MOTOR CONTROLLER - INTERFAZ PUBLICA
// =====================================================

namespace MotorController
{
    void begin(
        uint16_t currentMa,
        uint16_t microsteps,
        float maxSpeed,
        float acceleration
    );

    void configure(
        uint16_t currentMa,
        uint16_t microsteps,
        float maxSpeed,
        float acceleration
    );

    void enable();
    void disable();

    bool isEnabled();

    void setSpeed(float stepsPerSecond);
    float getSpeed();

    void setCurrentPosition(long position);
    long getCurrentPosition();

    void moveRelative(long steps);
    long distanceToGo();

    bool run();
    bool runSpeed();

    uint8_t getIFCNT();
    uint32_t getGCONF();
    uint32_t getCHOPCONF();
    uint32_t getDRVStatus();

    uint8_t getIRUN();
    uint8_t getIHOLD();
    uint16_t getMicrosteps();
}
