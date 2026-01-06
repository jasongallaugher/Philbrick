"""Component registry for the Philbrick analog computer emulator.

Provides centralized registration and factory functions for all component types,
including both built-in components and user-defined subcircuits.
"""

from typing import TYPE_CHECKING

from engine.component import Component
from engine.components.sources import VoltageSource
from engine.components.integrator import Integrator
from engine.components.math import (
    Summer,
    Coefficient,
    Inverter,
    Multiplier,
    Comparator,
    Limiter,
    Exp,
    Divider,
    DotProduct,
    Max,
    Constant,
)
from engine.components.generators import TriangleWave, SawtoothWave, SquareWave, PiecewiseLinear

if TYPE_CHECKING:
    from engine.subcircuit import SubcircuitDef


# Component type registry: maps type name strings to component classes
COMPONENTS: dict[str, type[Component]] = {
    "VoltageSource": VoltageSource,
    "Integrator": Integrator,
    "Summer": Summer,
    "Coefficient": Coefficient,
    "Inverter": Inverter,
    "Multiplier": Multiplier,
    "Comparator": Comparator,
    "Limiter": Limiter,
    "Exp": Exp,
    "Divider": Divider,
    "DotProduct": DotProduct,
    "Max": Max,
    "Constant": Constant,
    "TriangleWave": TriangleWave,
    "SawtoothWave": SawtoothWave,
    "SquareWave": SquareWave,
    "PiecewiseLinear": PiecewiseLinear,
}

# Subcircuit registry: maps type name strings to subcircuit definitions
SUBCIRCUITS: dict[str, "SubcircuitDef"] = {}


def get_component_class(type_name: str) -> type[Component]:
    """Get component class by type name.

    Args:
        type_name: Name of the component type (e.g., "Integrator")

    Returns:
        Component class corresponding to the type name

    Raises:
        KeyError: If type_name is not registered
    """
    return COMPONENTS[type_name]


def register_subcircuit(name: str, definition: "SubcircuitDef") -> None:
    """Register a subcircuit definition.

    Args:
        name: Unique name for the subcircuit type
        definition: SubcircuitDef object defining the subcircuit

    Raises:
        ValueError: If a subcircuit with this name is already registered
    """
    if name in SUBCIRCUITS:
        raise ValueError(f"Subcircuit '{name}' is already registered")
    SUBCIRCUITS[name] = definition


def get_subcircuit_def(name: str) -> "SubcircuitDef":
    """Get a subcircuit definition by name.

    Args:
        name: Name of the subcircuit type

    Returns:
        SubcircuitDef corresponding to the name

    Raises:
        KeyError: If the subcircuit is not registered
    """
    return SUBCIRCUITS[name]


def is_subcircuit(name: str) -> bool:
    """Check if a type name refers to a registered subcircuit.

    Args:
        name: Type name to check

    Returns:
        True if the name is a registered subcircuit, False otherwise
    """
    return name in SUBCIRCUITS


def create_component(
    type_name: str, name: str, params: dict | None = None
) -> Component:
    """Create a component instance from a type name.

    Handles both built-in component types and registered subcircuits.
    For subcircuits, machine and patchbay must be provided in params.

    Args:
        type_name: Name of the component type (e.g., "Integrator") or subcircuit
        name: Instance name for the component
        params: Optional dict of constructor parameters (passed as **kwargs)
                For subcircuits, must include "machine" and "patchbay" keys

    Returns:
        Instantiated component or subcircuit component

    Raises:
        KeyError: If type_name is not registered as a component or subcircuit
        TypeError: If params don't match the component's constructor signature
        ValueError: For subcircuits, if machine or patchbay are not in params
    """
    # Check if this is a subcircuit first
    if is_subcircuit(type_name):
        # Import here to avoid circular dependency
        from engine.subcircuit import SubcircuitComponent

        if params is None:
            raise ValueError(
                f"Subcircuit '{type_name}' requires 'machine' and 'patchbay' "
                f"in params"
            )

        machine = params.get("machine")
        patchbay = params.get("patchbay")

        if machine is None or patchbay is None:
            raise ValueError(
                f"Subcircuit '{type_name}' requires both 'machine' and "
                f"'patchbay' in params"
            )

        subcircuit_def = get_subcircuit_def(type_name)
        return SubcircuitComponent(name, subcircuit_def, machine, patchbay)

    # Fall through to regular component creation
    component_class = get_component_class(type_name)
    if params is None:
        return component_class(name)
    return component_class(name, **params)


def list_component_types() -> list[str]:
    """Get list of all registered component and subcircuit type names.

    Returns:
        Sorted list of all available component and subcircuit type names
    """
    return sorted(set(COMPONENTS.keys()) | set(SUBCIRCUITS.keys()))
