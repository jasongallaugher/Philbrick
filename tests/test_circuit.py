import pytest
from engine.circuit import (
    CircuitDef, ComponentDef, PatchDef,
    parse_port_ref, CircuitLoader, CircuitSaver
)
from engine.machine import Machine
from engine.patchbay import PatchBay
from engine.components.integrator import Integrator
from engine.components.math import Coefficient


def test_parse_port_ref() -> None:
    """Verify 'INT1.out' parses to ('INT1', 'out')."""
    component_name, port_name = parse_port_ref("INT1.out")
    assert component_name == "INT1"
    assert port_name == "out"


def test_parse_port_ref_invalid() -> None:
    """Verify bad format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid port reference"):
        parse_port_ref("invalid")

    # "too.many.dots" is valid - splits as ("too", "many.dots")
    component, port = parse_port_ref("too.many.dots")
    assert component == "too"
    assert port == "many.dots"


def test_circuit_def_from_dict() -> None:
    """Create CircuitDef from a dict, verify fields."""
    data = {
        "name": "test_circuit",
        "description": "A test circuit",
        "components": [
            {"name": "INT1", "type": "Integrator", "params": {"initial": 1.0}},
            {"name": "COEF1", "type": "Coefficient", "params": {"k": 0.5}},
        ],
        "patches": [
            ["COEF1.out", "INT1.in"],
        ],
    }

    circuit_def = CircuitDef.from_dict(data)

    assert circuit_def.name == "test_circuit"
    assert circuit_def.description == "A test circuit"
    assert len(circuit_def.components) == 2
    assert circuit_def.components[0].name == "INT1"
    assert circuit_def.components[0].type == "Integrator"
    assert circuit_def.components[0].params == {"initial": 1.0}
    assert circuit_def.components[1].name == "COEF1"
    assert circuit_def.components[1].type == "Coefficient"
    assert circuit_def.components[1].params == {"k": 0.5}
    assert len(circuit_def.patches) == 1
    assert circuit_def.patches[0].source == "COEF1.out"
    assert circuit_def.patches[0].dest == "INT1.in"


def test_circuit_loader_from_dict() -> None:
    """Load a circuit dict, verify machine has components."""
    machine = Machine(dt=0.001)
    patchbay = PatchBay()

    data = {
        "name": "simple_circuit",
        "components": [
            {"name": "INT1", "type": "Integrator", "params": {"initial": 0.0, "gain": 1.0}},
            {"name": "COEF1", "type": "Coefficient", "params": {"k": 2.0}},
        ],
        "patches": [],
    }

    circuit_def = CircuitDef.from_dict(data)
    loader = CircuitLoader(machine, patchbay)
    loader.load(circuit_def)

    assert len(machine.components) == 2
    assert machine.components[0].name == "INT1"
    assert isinstance(machine.components[0], Integrator)
    assert machine.components[1].name == "COEF1"
    assert isinstance(machine.components[1], Coefficient)


def test_circuit_loader_patches() -> None:
    """Verify patches are connected correctly."""
    machine = Machine(dt=0.001)
    patchbay = PatchBay()

    data = {
        "name": "patched_circuit",
        "components": [
            {"name": "COEF1", "type": "Coefficient", "params": {"k": 2.0}},
            {"name": "INT1", "type": "Integrator", "params": {"initial": 0.0}},
        ],
        "patches": [
            ["COEF1.out", "INT1.in"],
        ],
    }

    circuit_def = CircuitDef.from_dict(data)
    loader = CircuitLoader(machine, patchbay)
    loader.load(circuit_def)

    # Find the components
    coef1 = machine.components[0]
    int1 = machine.components[1]

    # Write a value to coefficient input and verify it propagates to integrator input
    coef1.inputs["in"].write(5.0)
    coef1.step(0.001)  # Compute coefficient output
    patchbay.propagate()  # Propagate through patch

    assert int1.inputs["in"].read() == 10.0  # 5.0 * 2.0


def test_circuit_round_trip() -> None:
    """Save a circuit, load it back, verify same structure."""
    # Create a machine with components manually
    machine1 = Machine(dt=0.001)
    patchbay1 = PatchBay()

    int1 = Integrator("INT1", initial=1.0, gain=2.0)
    coef1 = Coefficient("COEF1", k=0.5)

    machine1.add(int1)
    machine1.add(coef1)

    # Create patches manually
    patchbay1.connect(coef1.outputs["out"], int1.inputs["in"])

    # Save to dict using CircuitSaver.to_dict
    saver = CircuitSaver(machine1, patchbay1)
    circuit_dict = saver.to_dict(name="round_trip_test", description="Round trip test circuit")

    # Verify saved structure
    assert circuit_dict["name"] == "round_trip_test"
    assert circuit_dict["description"] == "Round trip test circuit"
    assert len(circuit_dict["components"]) == 2
    assert len(circuit_dict["patches"]) == 1

    # Load from dict using CircuitLoader.from_dict
    machine2 = Machine(dt=0.001)
    patchbay2 = PatchBay()

    circuit_def = CircuitDef.from_dict(circuit_dict)
    loader = CircuitLoader(machine2, patchbay2)
    loader.load(circuit_def)

    # Verify component names and types match
    assert len(machine2.components) == 2

    # Find components by name
    loaded_int1 = next(c for c in machine2.components if c.name == "INT1")
    loaded_coef1 = next(c for c in machine2.components if c.name == "COEF1")

    assert isinstance(loaded_int1, Integrator)
    assert isinstance(loaded_coef1, Coefficient)

    # Verify parameters were preserved
    assert loaded_int1.initial == 1.0
    assert loaded_int1.gain == 2.0
    assert loaded_coef1.k == 0.5

    # Verify patch count matches
    # Test connectivity by writing to coefficient and propagating
    loaded_coef1.inputs["in"].write(4.0)
    loaded_coef1.step(0.001)
    patchbay2.propagate()

    assert loaded_int1.inputs["in"].read() == 2.0  # 4.0 * 0.5
