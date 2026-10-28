#pragma once

#include <Arduino.h>

// Inicializa las entradas con resistencias pull-up internas.
void initLimitSwitches();

// Devuelve true cuando el final izquierdo está activado.
bool isLeftLimitActive();

// Devuelve true cuando el final derecho está activado.
bool isRightLimitActive();
