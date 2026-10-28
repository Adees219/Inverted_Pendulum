#include "ControlSystem.h"
#include <math.h>

namespace ControlSystem {
float wrap180(float deg) {
  while (deg > 180.0f) deg -= 360.0f;
  while (deg <= -180.0f) deg += 360.0f;
  return deg;
}
void resetPID(PIDMemory& memory) {
  memory.integral = 0.0f;
  memory.prevError = 0.0f;
}
float computePID(const PIDGains& gains, float thetaDeg, float dt, PIDMemory& memory) {
  const float reference = gains.up ? 0.0f : 180.0f;
  const float error = wrap180(reference - thetaDeg);
  memory.integral += error * dt;
  if (memory.integral > 100.0f) memory.integral = 100.0f;
  if (memory.integral < -100.0f) memory.integral = -100.0f;
  const float derivative = dt > 0.0f ? (error - memory.prevError) / dt : 0.0f;
  memory.prevError = error;
  return gains.kp * error + gains.ki * memory.integral + gains.kd * derivative;
}
float computeStateFeedback(const StateGains& gains, const StateVector& state) {
  const float x[4] = {state.thetaDeg, state.omegaDegS,
                      state.positionMm - gains.referenceMm, state.velocityMmS};
  float u = 0.0f;
  for (int i = 0; i < 4; ++i) u -= gains.k[i] * x[i];
  return u;
}
}
