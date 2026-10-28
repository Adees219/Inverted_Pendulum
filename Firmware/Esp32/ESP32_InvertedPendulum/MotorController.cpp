
#include "MotorController.h"
#include "HardwareConfig.h"

#include <TMCStepper.h>
#include <AccelStepper.h>

// =====================================================
// OBJETOS INTERNOS
// =====================================================

namespace
{
    HardwareSerial TMCSerial(2);

    TMC2209Stepper driver(
        &TMCSerial,
        R_SENSE,
        DRIVER_ADDR
    );

    AccelStepper stepper(
        AccelStepper::DRIVER,
        STEP_PIN,
        DIR_PIN
    );

    bool enabled = false;
}

// =====================================================
// IMPLEMENTACION
// =====================================================

namespace MotorController
{
    void begin(
        uint16_t currentMa,
        uint16_t microsteps,
        float maxSpeed,
        float acceleration
    )
    {
        digitalWrite(EN_PIN, HIGH);
        pinMode(EN_PIN, OUTPUT);

        pinMode(STEP_PIN, OUTPUT);
        pinMode(DIR_PIN, OUTPUT);

        digitalWrite(STEP_PIN, LOW);

        TMCSerial.begin(
            115200,
            SERIAL_8N1,
            TMC_RX,
            TMC_TX
        );

        driver.begin();
        driver.toff(4);
        driver.blank_time(24);

        configure(
            currentMa,
            microsteps,
            maxSpeed,
            acceleration
        );

        stepper.setMinPulseWidth(3);

        disable();
    }

    void configure(
        uint16_t currentMa,
        uint16_t microsteps,
        float maxSpeed,
        float acceleration
    )
    {
        driver.rms_current(currentMa);
        driver.microsteps(microsteps);

        stepper.setMaxSpeed(maxSpeed);
        stepper.setAcceleration(acceleration);
    }

    void enable()
    {
        digitalWrite(EN_PIN, LOW);
        enabled = true;
    }

    void disable()
    {
        stepper.setSpeed(0);
        digitalWrite(EN_PIN, HIGH);
        enabled = false;
    }

    bool isEnabled()
    {
        return digitalRead(EN_PIN) == LOW;
    }

    void setSpeed(float stepsPerSecond)
    {
        stepper.setSpeed(stepsPerSecond);
    }

    float getSpeed()
    {
        return stepper.speed();
    }

    void setCurrentPosition(long position)
    {
        stepper.setCurrentPosition(position);
    }

    long getCurrentPosition()
    {
        return stepper.currentPosition();
    }

    void moveRelative(long steps)
    {
        stepper.move(steps);
    }

    long distanceToGo()
    {
        return stepper.distanceToGo();
    }

    bool run()
    {
        return stepper.run();
    }

    bool runSpeed()
    {
        return stepper.runSpeed();
    }

    uint8_t getIFCNT()
    {
        return driver.IFCNT();
    }

    uint32_t getGCONF()
    {
        return driver.GCONF();
    }

    uint32_t getCHOPCONF()
    {
        return driver.CHOPCONF();
    }

    uint32_t getDRVStatus()
    {
        return driver.DRV_STATUS();
    }

    uint8_t getIRUN()
    {
        return driver.irun();
    }

    uint8_t getIHOLD()
    {
        return driver.ihold();
    }

    uint16_t getMicrosteps()
    {
        return driver.microsteps();
    }
}
