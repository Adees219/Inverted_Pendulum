
#include "LimitSwitches.h"
#include "HardwareConfig.h"

// =====================================================
// INICIALIZACION
// =====================================================

void initLimitSwitches()
{
    pinMode(LIMIT_LEFT, INPUT_PULLUP);
    pinMode(LIMIT_RIGHT, INPUT_PULLUP);
}

// =====================================================
// LECTURA DE FINALES DE CARRERA
// =====================================================

// Contactos NC:
// LOW  = funcionamiento normal
// HIGH = pulsado o circuito abierto

bool isLeftLimitActive()
{
    return digitalRead(LIMIT_LEFT) == HIGH;
}

bool isRightLimitActive()
{
    return digitalRead(LIMIT_RIGHT) == HIGH;
}
