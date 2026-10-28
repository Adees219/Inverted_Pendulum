#pragma once
#include <stdint.h>

// Solo calculos matematicos. No habilita el motor ni accede a GPIO.
namespace ControlSystem {
struct PIDGains { float kp, ki, kd; bool up; };
struct StateGains { float k[4]; float referenceMm; };
struct StateVector { float thetaDeg, omegaDegS, positionMm, velocityMmS; };
struct PIDMemory { float integral, prevError; };
float wrap180(float deg);
void resetPID(PIDMemory& memory);
float computePID(const PIDGains& gains, float thetaDeg, float dt, PIDMemory& memory);
float computeStateFeedback(const StateGains& gains, const StateVector& state);
}
