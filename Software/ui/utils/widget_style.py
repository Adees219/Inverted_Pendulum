# Documento de valores predefinidos para definir el estilo de las ventanas: dimensiones/colores/font de los widgets y los aplica

from ui.constants.ui_constants import (
    CONTROL_HEIGHT,
    BUTTON_HEIGHT,
    LAYOUT_MARGIN,
    LAYOUT_SPACING,
    GROUP_SPACING,
    GROUP_MIN_WIDTH,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_YELLOW
)

def set_control_height(*widgets):

    for widget in widgets:

        widget.setMinimumHeight(
            CONTROL_HEIGHT
        )

def set_button_height(*buttons):

    for button in buttons:

        button.setMinimumHeight(
            BUTTON_HEIGHT
        ) 

def configure_group_width(*groups):

    for group in groups:

        group.setMinimumWidth(
            GROUP_MIN_WIDTH
        )

def configure_layout(layout):

    layout.setSpacing(
        LAYOUT_SPACING
    )

    layout.setContentsMargins(
        LAYOUT_MARGIN,
        LAYOUT_MARGIN,
        LAYOUT_MARGIN,
        LAYOUT_MARGIN
    )

def configure_sub_layout(layout):

    layout.setSpacing(
        GROUP_SPACING
    )

def set_primary_button(*buttons):

    for button in buttons:

        button.setMinimumHeight(
            BUTTON_HEIGHT
        )

        button.setDefault(True)
        button.setAutoDefault(True)

def set_secondary_button(*buttons):

    for button in buttons:

        button.setMinimumHeight(
            BUTTON_HEIGHT
        )
        button.setAutoDefault(False)

def set_status(label, text, color):

    label.setText(
        text
    )

    label.setStyleSheet(
            f"color:{color};"
    )

