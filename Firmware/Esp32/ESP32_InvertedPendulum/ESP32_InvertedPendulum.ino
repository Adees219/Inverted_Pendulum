//UNIVERSIDAD DEL VALLE DE GUATEMALA
//Anderson Daniel Eduardo Escobar Sandoval - 21712
//Interfaz gráfica - Proyecto de graduación: Acondicionamiento de un sistema de péndulo invertido 

//prueba
// {"type":"system_config","current_ma":800,"microsteps":16,"max_speed_steps_s":32000,"acceleration_steps_s2":150000,"control_period_us":1000,"telemetry_period_ms":20,"encoder_offset_deg":283.0}

//motor En
//{"type":"command","command":"test_enable","enabled":true}
//{"type":"command","command":"test_enable","enabled":false}

//motor DIR
//{"type":"command","command":"test_direction","direction":"right"} GPIO 12 high
//{"type":"command","command":"test_direction","direction":"left"}

//Finales carrera
//{"type":"command","command":"test_limits"}

// motor step
// {"type":"command","command":"test_motor","speed_steps_s":2} GPIO 14 High
// {"type":"command","command":"test_motor","speed_steps_s":0}

//motor move
//{"type":"command","command":"test_move","steps":200}
//{"type":"command","command":"stop"}

//{"type":"command","command":"test_motor","speed_steps_s":5}
// {"type":"command","command":"test_motor","speed_steps_s":-5}

//status
// {"type":"command","command":"motor_status"}

//{"type":"command","command":"telemetry","enabled":false}

//{"type":"command","command":"driver_status"}

//as5600
//{"type":"command","command":"sensor_status"}
//{"type":"command","command":"encoder_raw"}

//{"type":"command","command":"get_config"}

// Firmware de preintegracion - pendulo invertido / ESP32-WROOM-32
// ArduinoJson 7, TMCStepper 0.7.3, AccelStepper 1.64
// IMPORTANTE: los controladores estan BLOQUEADOS hasta verificar el hardware.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <math.h>
#include <string.h>

#include "HardwareConfig.h"
#include "MotorController.h"
#include "LimitSwitches.h"
#include "Sensors.h"
#include "Protocol.h"
#include "NetworkManager.h"
#include "ControlSystem.h"

using Protocol::sendJson;
using Protocol::sendAck;
using Protocol::sendError;

constexpr int32_t BENCH_MAX_MOVE_STEPS = 200;
constexpr float BENCH_MOVE_MAX_SPEED = 200.0f;
constexpr float BENCH_MOVE_ACCEL = 100.0f;



struct SystemConfig {
  uint16_t currentMa=400, microsteps=16;
  uint32_t maxSpeedStepsS=32000, accelerationStepsS2=150000;
  uint32_t controlPeriodUs=1000, telemetryPeriodMs=20;
  float encoderOffsetDeg=283.0f;
};
struct PIDConfig { float kp=0,ki=0,kd=0; bool up=true; bool valid=false; };
struct StateConfig { float k[4]={0,0,0,0}; float referenceMm=0; bool valid=false; };
struct StateData {
  float thetaDeg=0, omegaDegS=0, positionMm=0, velocityMmS=0;
  float controlStepsS=0;
  bool pendValid=false, cartValid=false;
  bool pendDisplayValid=false, cartDisplayValid=false;
  bool pendMagnetWeak=false, cartMagnetWeak=false;
};
enum class Mode : uint8_t { READY, RUN_PID, RUN_STATE, FAULT };
SystemConfig systemConfig;
PIDConfig pidConfig;
StateConfig stateConfig;
StateData states;
Mode mode=Mode::READY;
bool motorTestRunning=false, motorInitialized=false, sensorsInitialized=false;
bool motorPositionTest=false;
uint32_t motorTestStartMs = 0;
uint32_t lastControlUs=0, lastTelemetryMs=0, lastSensorUs=0;
// Telemetría desactivada inicialmente para diagnósticos
bool telemetryEnabled = false;
uint16_t prevPendRaw=0, prevCartRaw=0;
bool pendPrev=false, cartPrev=false;
int32_t cartAccumCounts=0;
float lastThetaDeg=0, lastPositionMm=0;
float integral=0, prevError=0;
// FALTA medir conversion mecanica real: NO inventar mm por vuelta.
float cartMmPerEncoderTurn=NAN;
// El offset angular y las convenciones de equilibrio requieren calibracion.

// =====================================================
// ESTADO DEL MOTOR
// =====================================================

float motorTargetSpeed = 0.0f;

bool motorFault = false;

const char* modeName() {
  switch(mode) { case Mode::RUN_PID: return "pid"; case Mode::RUN_STATE: return "state"; default: return "none"; }
}
const char* stateName() {
  if(mode==Mode::FAULT) return "error";
  if(mode==Mode::RUN_PID || mode==Mode::RUN_STATE) return "running";
  return "ready";
}
void sendStatus() {
  JsonDocument d; d["type"]="status"; d["state"]=stateName(); d["control_mode"]=modeName(); sendJson(d);
}
void disableMotor()
{
    motorTestRunning = false;
    motorPositionTest = false;
    motorTargetSpeed = 0.0f;

    states.controlStepsS = 0;

    MotorController::disable();
}
void initMotor()
{
    MotorController::begin(
        systemConfig.currentMa,
        systemConfig.microsteps,
        200.0f,
        100.0f
    );

    motorInitialized = true;
}


float wrap180(float deg) { return ControlSystem::wrap180(deg); }
// Sensor validation: I2C success alone does not prove a usable magnetic field.
// MD must be set, while ML and MH must both be clear.
constexpr uint32_t SENSOR_MAX_AGE_MS = 100;
uint32_t pendLastValidMs = 0;
uint32_t cartLastValidMs = 0;

// Display accepts MD even with ML; control requires MD and neither ML nor MH.
// A weak-field reading is provisional and must not enable closed-loop control.
bool readMagneticQuality(Sensors::Encoder encoder, bool& detected, bool& weak, bool& strong) {
  uint8_t status = 0;
  detected = weak = strong = false;
  if (!Sensors::readStatus(encoder, status)) return false;
  detected = (status & 0x20) != 0;
  weak = (status & 0x10) != 0;
  strong = (status & 0x08) != 0;
  return true;
}

void updateSensors() {
  const uint32_t nowUs = micros();
  if ((uint32_t)(nowUs - lastSensorUs) < 5000) return;
  const float dt = lastSensorUs ? (float)(uint32_t)(nowUs-lastSensorUs)*1e-6f : 0.0f;
  lastSensorUs = nowUs;
  const uint32_t nowMs = millis();
  uint16_t raw = 0;

  bool pendDetected=false, pendWeak=false, pendStrong=false;
  const bool pendStatusOK = readMagneticQuality(Sensors::Encoder::Pendulum, pendDetected, pendWeak, pendStrong);
  // DIAGNOSTICO VISUAL: usar RAW si I2C responde, incluso sin MD o con ML/MH.
  // La validez para control se evalua por separado y permanece estricta.
  const bool pendOK = Sensors::readRaw(Sensors::Encoder::Pendulum, raw);
  states.pendMagnetWeak = pendStatusOK && pendWeak;
  if (pendOK) {
    const float angle = wrap180((float)raw * (360.0f/4096.0f) - systemConfig.encoderOffsetDeg);
    if (pendPrev && dt > 0.0f) states.omegaDegS = wrap180(angle-lastThetaDeg)/dt;
    else states.omegaDegS = 0.0f;
    states.thetaDeg = angle;
    lastThetaDeg = angle;
    pendPrev = true;
    prevPendRaw = raw;
    pendLastValidMs = nowMs;
  } else {
    pendPrev = false;
  }
  states.pendDisplayValid = pendOK && (uint32_t)(nowMs-pendLastValidMs) <= SENSOR_MAX_AGE_MS;
  states.pendValid = states.pendDisplayValid && pendStatusOK &&
                     pendDetected && !pendWeak && !pendStrong;

  bool cartDetected=false, cartWeak=false, cartStrong=false;
  const bool cartStatusOK = readMagneticQuality(Sensors::Encoder::Cart, cartDetected, cartWeak, cartStrong);
  // La lectura RAW del carro tambien se independiza del estado magnetico.
  const bool cartOK = Sensors::readRaw(Sensors::Encoder::Cart, raw);
  states.cartMagnetWeak = cartStatusOK && cartWeak;
  if (cartOK) {
    if (!cartPrev) { prevCartRaw = raw; cartPrev = true; }
    int diff = (int)raw-(int)prevCartRaw;
    if (diff > 2048) diff -= 4096;
    if (diff < -2048) diff += 4096;
    cartAccumCounts += diff;
    prevCartRaw = raw;
    if (isfinite(cartMmPerEncoderTurn) && cartMmPerEncoderTurn > 0.0f) {
      states.positionMm = (float)cartAccumCounts*cartMmPerEncoderTurn/4096.0f;
      states.velocityMmS = dt > 0.0f ? (states.positionMm-lastPositionMm)/dt : 0.0f;
      lastPositionMm = states.positionMm;
      cartLastValidMs = nowMs;
    }
  } else {
    cartPrev = false;
  }
  // A physical conversion is required before cart position can be considered valid.
  states.cartDisplayValid = cartOK && isfinite(cartMmPerEncoderTurn) &&
                            cartMmPerEncoderTurn > 0.0f &&
                            (uint32_t)(nowMs-cartLastValidMs) <= SENSOR_MAX_AGE_MS;
  states.cartValid = states.cartDisplayValid && cartStatusOK &&
                     cartDetected && !cartWeak && !cartStrong;
}

bool applySystemConfig(const SystemConfig& cfg)
{
    if (mode != Mode::READY || motorTestRunning)
    {
        return false;
    }

    MotorController::configure(
        cfg.currentMa,
        cfg.microsteps,
        cfg.maxSpeedStepsS,
        cfg.accelerationStepsS2
    );

    return true;
}
void handleSystemConfig(JsonDocument& d) {
  Serial.println("[CONFIG] Procesando system_config");
  const char* keys[]={"current_ma","microsteps","max_speed_steps_s","acceleration_steps_s2","control_period_us","telemetry_period_ms"};
  for(const char* key:keys) {
    if(!d[key].is<int>()) { sendError("INVALID_CONFIG","Missing or invalid integer field"); return; }
  }
  if(!(d["encoder_offset_deg"].is<float>() || d["encoder_offset_deg"].is<int>())) {
    sendError("INVALID_CONFIG","Invalid encoder_offset_deg"); return;
  }
  int current=d["current_ma"], micro=d["microsteps"], speed=d["max_speed_steps_s"];
  int accel=d["acceleration_steps_s2"], ctrl=d["control_period_us"], tele=d["telemetry_period_ms"];
  float offset=d["encoder_offset_deg"].as<float>();
  bool validMicro=(micro==1||micro==2||micro==4||micro==8||micro==16||micro==32||micro==64||micro==128);
  if(current<300||current>1600||!validMicro||speed<300||speed>100000||accel<300||accel>150000||ctrl<500||ctrl>100000||tele<10||tele>1000||!isfinite(offset)||offset<0||offset>360) {
    sendError("INVALID_CONFIG","system_config out of range"); return;
  }
  SystemConfig candidate{(uint16_t)current,(uint16_t)micro,(uint32_t)speed,(uint32_t)accel,(uint32_t)ctrl,(uint32_t)tele,offset};
  if(!applySystemConfig(candidate)) { sendError("MOTOR_ERROR","Configuration rejected while active"); return; }
  systemConfig=candidate; sendAck("system_config");
}
void handlePIDConfig(JsonDocument& d) {
  if(mode!=Mode::READY) { sendError("INVALID_CONFIG","Stop control before configuration"); return; }
  if(!(d["kp"].is<float>()||d["kp"].is<int>()) || !(d["ki"].is<float>()||d["ki"].is<int>()) || !(d["kd"].is<float>()||d["kd"].is<int>()) || !d["equilibrium"].is<const char*>()) {
    sendError("INVALID_CONFIG","Invalid PID fields"); return;
  }
  const char* eq=d["equilibrium"];
  if(strcmp(eq,"up")!=0 && strcmp(eq,"down")!=0) { sendError("INVALID_CONFIG","Invalid equilibrium"); return; }
  PIDConfig candidate; candidate.kp=d["kp"].as<float>(); candidate.ki=d["ki"].as<float>(); candidate.kd=d["kd"].as<float>(); candidate.up=strcmp(eq,"up")==0;
  if(!isfinite(candidate.kp)||!isfinite(candidate.ki)||!isfinite(candidate.kd)) { sendError("INVALID_CONFIG","Nonfinite PID gains"); return; }
  candidate.valid=true; pidConfig=candidate; sendAck("pid_config");
}
void handleStateConfig(JsonDocument& d) {
  if(mode!=Mode::READY) { sendError("INVALID_CONFIG","Stop control before configuration"); return; }
  StateConfig candidate;
  const char* names[]={"k1","k2","k3","k4"};
  for(int i=0;i<4;i++) {
    if(!(d[names[i]].is<float>()||d[names[i]].is<int>())) { sendError("INVALID_CONFIG","Invalid state gain"); return; }
    candidate.k[i]=d[names[i]].as<float>();
    if(!isfinite(candidate.k[i])) { sendError("INVALID_CONFIG","Nonfinite state gain"); return; }
  }
  if(!(d["reference_mm"].is<float>()||d["reference_mm"].is<int>())) { sendError("INVALID_CONFIG","Invalid reference_mm"); return; }
  candidate.referenceMm=d["reference_mm"].as<float>();
  if(!isfinite(candidate.referenceMm)) { sendError("INVALID_CONFIG","Nonfinite reference"); return; }
  candidate.valid=true; stateConfig=candidate; sendAck("state_config");
}
void enterFault(const char* code,const char* message) {
  disableMotor(); mode=Mode::FAULT; sendError(code,message); sendStatus();
}
void stopController()
{
    disableMotor();

    integral = 0;
    prevError = 0;

    // Un STOP no debe borrar una condición de fallo.
    if (mode != Mode::FAULT)
    {
        mode = Mode::READY;
    }

    sendStatus();
}
void resetController() {
  disableMotor();
  if(isLeftLimitActive() || isRightLimitActive()) {
    sendError("LIMIT_ACTIVE","Cannot reset while limit is active"); return;
  }
  mode=Mode::READY; integral=0; prevError=0;
  cartAccumCounts=0; cartPrev=false; pendPrev=false;
  MotorController::setCurrentPosition(0); sendStatus();
}
void setMotorVelocity(float stepsPerSec) {
  if(!isfinite(stepsPerSec)) { enterFault("CONTROL_ERROR","Nonfinite motor command"); return; }
  float cap=(float)systemConfig.maxSpeedStepsS;
  if(stepsPerSec>cap) stepsPerSec=cap;
  if(stepsPerSec< -cap) stepsPerSec=-cap;
  if((stepsPerSec<0 && isLeftLimitActive()) || (stepsPerSec>0 && isRightLimitActive())) {
    enterFault(stepsPerSec<0 ? "LIMIT_LEFT":"LIMIT_RIGHT","Limit switch active"); return;
  }
  states.controlStepsS=stepsPerSec; MotorController::setSpeed(stepsPerSec);
}
// Adaptadores: mantienen los nombres originales utilizados por el scheduler.
float computePID(float dt) {
  ControlSystem::PIDGains gains{pidConfig.kp, pidConfig.ki, pidConfig.kd, pidConfig.up};
  ControlSystem::PIDMemory memory{integral, prevError};
  float u = ControlSystem::computePID(gains, states.thetaDeg, dt, memory);
  integral = memory.integral;
  prevError = memory.prevError;
  return u;
}
float computeStateFeedback() {
  ControlSystem::StateGains gains{{stateConfig.k[0], stateConfig.k[1], stateConfig.k[2], stateConfig.k[3]}, stateConfig.referenceMm};
  ControlSystem::StateVector state{states.thetaDeg, states.omegaDegS, states.positionMm, states.velocityMmS};
  return ControlSystem::computeStateFeedback(gains, state);
}
void runControlLoop() {
  uint32_t now=micros();
  if((uint32_t)(now-lastControlUs)<systemConfig.controlPeriodUs) return;
  float dt=lastControlUs ? (float)(uint32_t)(now-lastControlUs)*1e-6f : 0;
  lastControlUs=now;
  if(mode!=Mode::RUN_PID && mode!=Mode::RUN_STATE) return;
  if(!ALLOW_CLOSED_LOOP || !states.pendValid ||
     (mode==Mode::RUN_STATE && !states.cartValid) || dt<=0) {
    enterFault("CONTROL_ERROR","Closed-loop prerequisites not satisfied"); return;
  }
  float u=mode==Mode::RUN_PID ? computePID(dt) : computeStateFeedback();
  setMotorVelocity(u);
}
void updateMotor() {
  if (motorTestRunning) {
    if ((uint32_t)(millis()-motorTestStartMs)>=BENCH_TIMEOUT_MS) {
      disableMotor(); sendStatus(); return;
    }
    // In position mode, direction is determined by distanceToGo(), not speed().
    long remaining = motorPositionTest ? MotorController::distanceToGo() : 0;
    float velocity = MotorController::getSpeed();
    bool towardLeft = motorPositionTest ? (remaining<0) : (velocity<0);
    bool towardRight = motorPositionTest ? (remaining>0) : (velocity>0);
    if ((towardLeft && isLeftLimitActive()) ||
        (towardRight && isRightLimitActive())) {
      enterFault(towardLeft ? "LIMIT_LEFT" : "LIMIT_RIGHT", "Limit activated during bench test");
      return;
    }
    if (motorPositionTest) {
      if (remaining==0) { disableMotor(); sendStatus(); return; }
      MotorController::run();
    } else {
      MotorController::runSpeed();
    }
    return;
  }
  if (mode==Mode::RUN_PID || mode==Mode::RUN_STATE) {
    float v=MotorController::getSpeed();
    if ((v<0 && isLeftLimitActive()) || (v>0 && isRightLimitActive())) {
      enterFault(v<0 ? "LIMIT_LEFT" : "LIMIT_RIGHT", "Limit switch active"); return;
    }
    MotorController::runSpeed();
  }
}
void sendTelemetry() {
  JsonDocument d; d["type"]="telemetry";
  if(states.pendDisplayValid) { d["angle_deg"]=states.thetaDeg; d["angular_velocity_deg_s"]=states.omegaDegS; }
  else { d["angle_deg"]=nullptr; d["angular_velocity_deg_s"]=nullptr; }
  if(states.cartDisplayValid) { d["position_mm"]=states.positionMm; d["linear_velocity_mm_s"]=states.velocityMmS; }
  else { d["position_mm"]=nullptr; d["linear_velocity_mm_s"]=nullptr; }
  d["pendulum_control_valid"] = states.pendValid;
  d["cart_control_valid"] = states.cartValid;
  d["pendulum_magnet_weak"] = states.pendMagnetWeak;
  d["cart_magnet_weak"] = states.cartMagnetWeak;
  d["control_effort_steps_s"]=states.controlStepsS;
  Protocol::sendTelemetry(d);
}
void runTelemetryScheduler()
{
    if (!telemetryEnabled)
    {
        return;
    }

    uint32_t now = millis();

    if (
        (uint32_t)(now - lastTelemetryMs)
        < systemConfig.telemetryPeriodMs
    )
    {
        return;
    }

    lastTelemetryMs = now;

    sendTelemetry();
}
void sendMotorStatus() {
  JsonDocument d; d["type"]="status"; d["component"]="motor";
  d["enabled"]=MotorController::isEnabled();
  d["direction_pin"]=digitalRead(DIR_PIN);
  d["speed_steps_s"]=MotorController::getSpeed();
  d["position_steps"]=MotorController::getCurrentPosition();
  d["test_running"]=motorTestRunning;
  d["position_test"]=motorPositionTest;
  d["distance_to_go"]=MotorController::distanceToGo();
  d["left_limit"]=isLeftLimitActive(); d["right_limit"]=isRightLimitActive(); sendJson(d);
}
void sendDriverStatus()
{
    JsonDocument d;

    d["type"] = "status";
    d["component"] = "tmc2209";

    d["ifcnt"] = MotorController::getIFCNT();
    d["gconf"] = MotorController::getGCONF();
    d["chopconf"] = MotorController::getCHOPCONF();

    d["irun"] = MotorController::getIRUN();
    d["ihold"] = MotorController::getIHOLD();

    d["microsteps"] = MotorController::getMicrosteps();
    d["drv_status"] = MotorController::getDRVStatus();

    sendJson(d);
}

void sendSystemConfigStatus()
{
    JsonDocument d;

    d["type"] = "status";
    d["component"] = "system_config";

    d["current_ma"] = systemConfig.currentMa;
    d["microsteps"] = systemConfig.microsteps;

    d["max_speed_steps_s"] =
        systemConfig.maxSpeedStepsS;

    d["acceleration_steps_s2"] =
        systemConfig.accelerationStepsS2;

    d["control_period_us"] =
        systemConfig.controlPeriodUs;

    d["telemetry_period_ms"] =
        systemConfig.telemetryPeriodMs;

    d["encoder_offset_deg"] =
        systemConfig.encoderOffsetDeg;

    sendJson(d);
}




void sendEncoderRawStatus()
{
    uint16_t pendRaw = 0;
    uint16_t cartRaw = 0;

    uint8_t pendStatus = 0;
    uint8_t cartStatus = 0;

    bool pendOK = Sensors::readRaw(Sensors::Encoder::Pendulum, pendRaw);
    bool cartOK = Sensors::readRaw(Sensors::Encoder::Cart, cartRaw);

    bool pendStatusOK = Sensors::readStatus(
        Sensors::Encoder::Pendulum, pendStatus
    );

    bool cartStatusOK = Sensors::readStatus(
        Sensors::Encoder::Cart, cartStatus
    );

    JsonDocument d;

    d["type"] = "status";
    d["component"] = "encoders";

    d["pendulum_valid"] = pendOK;
    d["cart_valid"] = cartOK;

    if (pendOK)
    {
        d["pendulum_raw"] = pendRaw;
        d["pendulum_deg"] =
            pendRaw * (360.0f / 4096.0f);
    }
    else
    {
        d["pendulum_raw"] = nullptr;
        d["pendulum_deg"] = nullptr;
    }

    if (cartOK)
    {
        d["cart_raw"] = cartRaw;
        d["cart_deg"] =
            cartRaw * (360.0f / 4096.0f);
    }
    else
    {
        d["cart_raw"] = nullptr;
        d["cart_deg"] = nullptr;
    }

    d["pendulum_status_valid"] = pendStatusOK;
    d["cart_status_valid"] = cartStatusOK;

    if (pendStatusOK)
    {
        d["pendulum_magnet_detected"] =
            (pendStatus & 0x20) != 0;

        d["pendulum_magnet_weak"] =
            (pendStatus & 0x10) != 0;

        d["pendulum_magnet_strong"] =
            (pendStatus & 0x08) != 0;
    }
    else
    {
        d["pendulum_magnet_detected"] = nullptr;
        d["pendulum_magnet_weak"] = nullptr;
        d["pendulum_magnet_strong"] = nullptr;
    }

    if (cartStatusOK)
    {
        d["cart_magnet_detected"] =
            (cartStatus & 0x20) != 0;

        d["cart_magnet_weak"] =
            (cartStatus & 0x10) != 0;

        d["cart_magnet_strong"] =
            (cartStatus & 0x08) != 0;
    }
    else
    {
        d["cart_magnet_detected"] = nullptr;
        d["cart_magnet_weak"] = nullptr;
        d["cart_magnet_strong"] = nullptr;
    }

    sendJson(d);
}



void handleCommand(JsonDocument& d) {

  if(!d["command"].is<const char*>()) { sendError("INVALID_COMMAND","Missing command"); return; }
  const char* cmd=d["command"];
  if (strcmp(cmd, "telemetry") == 0)
{
    if (!d["enabled"].is<bool>())
    {
        sendError(
            "INVALID_COMMAND",
            "Missing telemetry enabled field"
        );

        return;
    }

    telemetryEnabled = d["enabled"].as<bool>();

    lastTelemetryMs = millis();

    sendAck("command", cmd);

    return;
}
  if(strcmp(cmd,"stop")==0) { stopController(); sendAck("command",cmd); return; }
  if(strcmp(cmd,"reset")==0) { resetController(); sendAck("command",cmd); return; }
  if(strcmp(cmd,"motor_status")==0) { sendMotorStatus(); return; }
  if (strcmp(cmd, "driver_status") == 0)
  {
      sendDriverStatus();
      return;
  }
  if (strcmp(cmd, "get_config") == 0)
  {
      sendSystemConfigStatus();
      return;
  }
  if(strcmp(cmd,"sensor_status")==0) {
    JsonDocument r; r["type"]="status"; r["component"]="sensors";
    r["pendulum_as5600"]=Sensors::devicePresent(Sensors::Encoder::Pendulum);
    r["cart_as5600"]=Sensors::devicePresent(Sensors::Encoder::Cart); sendJson(r); return;
  }
  if (strcmp(cmd, "encoder_raw") == 0)
{
    sendEncoderRawStatus();
    return;
}
  if(strcmp(cmd,"test_limits")==0) {
    JsonDocument r; r["type"]="status"; r["component"]="limits";
    r["left_limit"]=isLeftLimitActive(); r["right_limit"]=isRightLimitActive(); sendJson(r); return;
  }
  if(strcmp(cmd,"start_pid")==0 || strcmp(cmd,"start_state")==0) {
    if(!ALLOW_CLOSED_LOOP) { sendError("NOT_READY","Closed-loop control locked pending physical validation"); return; }
    if(mode!=Mode::READY || !states.pendValid ||
       (strcmp(cmd,"start_state")==0 && !states.cartValid) ||
       isLeftLimitActive() || isRightLimitActive()) {
      sendError("NOT_READY","System not ready"); return;
    }
    bool pid=strcmp(cmd,"start_pid")==0;
    if(pid ? !pidConfig.valid : !stateConfig.valid) { sendError("CONTROL_NOT_CONFIGURED","Controller not configured"); return; }
    // Comprobar posicion inicial / zona de captura antes de habilitar motor.
    if(fabsf(states.thetaDeg)>10.0f) { sendError("NOT_READY","Pendulum outside initial capture region"); return; }
    integral=0; prevError=0; lastControlUs=micros();
    mode=pid?Mode::RUN_PID:Mode::RUN_STATE;
    MotorController::enable(); sendAck("command",cmd); sendStatus(); return;
  }
  if (strcmp(cmd,"test_move")==0) {
    if (!ALLOW_MOTOR_BENCH_TEST || mode!=Mode::READY || motorTestRunning) {
      sendError("INVALID_COMMAND","Bench movement unavailable"); return;
    }
    if (!d["steps"].is<int>()) {
      sendError("INVALID_COMMAND","steps must be an integer"); return;
    }
    int32_t delta=d["steps"].as<int32_t>();
    if (delta==0 || delta < -BENCH_MAX_MOVE_STEPS || delta > BENCH_MAX_MOVE_STEPS) {
      sendError("INVALID_COMMAND","steps out of bench range"); return;
    }
    if ((delta<0 && isLeftLimitActive()) || (delta>0 && isRightLimitActive())) {
      sendError("LIMIT_ACTIVE","Cannot move toward active limit"); return;
    }
    MotorController::configure(systemConfig.currentMa, systemConfig.microsteps, BENCH_MOVE_MAX_SPEED, BENCH_MOVE_ACCEL);
    MotorController::moveRelative(delta);
    motorPositionTest=true;
    motorTestRunning=true;
    motorTestStartMs=millis();
    MotorController::enable();
    sendAck("command",cmd); return;
  }
  if (strcmp(cmd, "test_motor") == 0)
{
    // Solo permitir pruebas cuando el sistema está preparado.
    if (!ALLOW_MOTOR_BENCH_TEST || mode != Mode::READY || motorTestRunning)
    {
        sendError(
            "INVALID_COMMAND",
            "Motor bench test unavailable"
        );
        return;
    }

    // Validar el tipo de dato.
    if (
        !d["speed_steps_s"].is<float>() &&
        !d["speed_steps_s"].is<int>()
    )
    {
        sendError(
            "INVALID_COMMAND",
            "Invalid motor speed"
        );
        return;
    }

    float speed = d["speed_steps_s"].as<float>();

    // Validar valores finitos y límites.
    if (!isfinite(speed) || fabsf(speed) > BENCH_MAX_SPEED)
    {
        sendError(
            "INVALID_COMMAND",
            "Bench speed out of range"
        );
        return;
    }

    // Velocidad cero equivale a detener.
    if (speed == 0.0f)
    {
        disableMotor();
        sendAck("command", cmd);
        return;
    }

    // Impedir movimiento hacia un límite activo.
    if (
        (speed < 0 && isLeftLimitActive()) ||
        (speed > 0 && isRightLimitActive())
    )
    {
        disableMotor();

        sendError(
            "LIMIT_ACTIVE",
            "Movement toward active limit rejected"
        );
        return;
    }

    motorTargetSpeed = speed;
    motorPositionTest = false;
    // La velocidad de prueba se limita por BENCH_MAX_SPEED.
    MotorController::setSpeed(speed);

    motorTestStartMs = millis();

    motorTestRunning = true;

    // Habilitar el TMC2209 solamente después de validar.
    MotorController::enable();

    sendAck("command", cmd);
    return;
}
  if (
      strcmp(cmd, "test_enable") == 0 ||
      strcmp(cmd, "test_direction") == 0
  )
  {
      sendError(
          "INVALID_COMMAND",
          "Legacy LED diagnostic disabled"
      );
      return;
  }
  sendError(
    "INVALID_COMMAND",
    "Unknown command"
);
}
void dispatchMessage(JsonDocument& d) {
  if(!d["type"].is<const char*>()) { sendError("INVALID_MESSAGE","Missing message type"); return; }
  const char* type=d["type"];
  if(strcmp(type,"system_config")==0) handleSystemConfig(d);
  else if(strcmp(type,"pid_config")==0) handlePIDConfig(d);
  else if(strcmp(type,"state_config")==0) handleStateConfig(d);
  else if(strcmp(type,"command")==0) handleCommand(d);
  else sendError("INVALID_MESSAGE","Unknown message type");
}
void dispatchTcpMessage(JsonDocument& d) {
  Serial.println("[TCP] JSON recibido");
  serializeJson(d, Serial);
  Serial.println();

  Protocol::setTcpReplyContext(true);
  dispatchMessage(d);
  Protocol::setTcpReplyContext(false);
}

void onTcpDisconnected() {
  if (motorTestRunning || mode == Mode::RUN_PID || mode == Mode::RUN_STATE) {
    disableMotor();
    mode = Mode::FAULT;
    Serial.println("[AP] Conexion perdida; motor deshabilitado");
  }
}

void setup() {
  // Estado seguro desde el primer instante posible del programa.
  digitalWrite(EN_PIN,HIGH); pinMode(EN_PIN,OUTPUT);
  Serial.begin(SERIAL_BAUD);
  Protocol::resetSerialBuffer();
  initLimitSwitches(); initMotor(); Sensors::begin(); sensorsInitialized=true;
  JsonDocument d; d["type"]="status"; d["state"]="starting"; d["control_mode"]="none"; sendJson(d);
  sendStatus();
  PendulumNetwork::begin();
}
void loop()
{
    Protocol::pollSerial(dispatchMessage);
    PendulumNetwork::poll(
    dispatchTcpMessage,
    onTcpDisconnected
);
    if (!motorTestRunning) updateSensors(); // Avoid I2C latency during bench motion.
    runControlLoop();
    updateMotor();
    runTelemetryScheduler();
}
