#include "Sensors.h"
#include "HardwareConfig.h"
#include <Wire.h>

namespace {
    TwoWire pendulumWire(0);
    TwoWire cartWire(1);

    TwoWire& busFor(Sensors::Encoder encoder) {
        return encoder == Sensors::Encoder::Pendulum ? pendulumWire : cartWire;
    }
}

namespace Sensors {
    void begin() {
        pendulumWire.begin(PEND_SDA, PEND_SCL);
        cartWire.begin(CART_SDA, CART_SCL);
        pendulumWire.setClock(100000);
        cartWire.setClock(100000);
    }

    bool devicePresent(Encoder encoder) {
        TwoWire& bus = busFor(encoder);
        bus.beginTransmission(AS5600_ADDR);
        return bus.endTransmission() == 0;
    }

    bool readRaw(Encoder encoder, uint16_t& raw) {
        TwoWire& bus = busFor(encoder);
        bus.beginTransmission(AS5600_ADDR);
        bus.write(0x0C);  // RAW ANGLE: registros 0x0C y 0x0D
        if (bus.endTransmission(false) != 0) return false;
        if (bus.requestFrom(AS5600_ADDR, (uint8_t)2) != (uint8_t)2) return false;
        raw = ((uint16_t)bus.read() << 8) | (uint16_t)bus.read();
        raw &= 0x0FFF;
        return true;
    }

    bool readStatus(Encoder encoder, uint8_t& status) {
        TwoWire& bus = busFor(encoder);
        bus.beginTransmission(AS5600_ADDR);
        bus.write(0x0B);  // STATUS
        if (bus.endTransmission(false) != 0) return false;
        if (bus.requestFrom(AS5600_ADDR, (uint8_t)1) != (uint8_t)1) return false;
        status = bus.read();
        return true;
    }
}
