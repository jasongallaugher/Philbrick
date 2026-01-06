"""Tests for SubcircuitComponent and registry integration.

Tests cover:
1. Basic SubcircuitComponent instantiation with simple I/O
2. Internal wiring between components within a subcircuit
3. Reset functionality with Integrators
4. Registry integration for creating subcircuits
5. Subcircuits appearing in list_component_types()
"""

import pytest
from engine.machine import Machine
from engine.patchbay import PatchBay
from engine.subcircuit import (
    SubcircuitDef,
    ComponentDef,
    PatchDef,
    SubcircuitComponent,
    instantiate_subcircuit,
)
from engine.registry import (
    create_component,
    list_component_types,
    register_subcircuit,
    SUBCIRCUITS,
)


# =============================================================================
# Test 1: SubcircuitComponent Basic Instantiation
# =============================================================================


def test_subcircuit_component_basic() -> None:
    """Create simple SubcircuitDef with one Coefficient, instantiate, verify I/O."""
    # Create a subcircuit with a single Coefficient component
    coeff_def = ComponentDef(name="COEFF1", type="Coefficient", params={"k": 2.0})

    subcircuit_def = SubcircuitDef(
        name="DoubleValue",
        description="Multiply input by 2",
        inputs=["in"],
        outputs=["out"],
        components=[coeff_def],
        input_map={"in": "COEFF1.in"},
        output_map={"out": "COEFF1.out"},
    )

    # Create machine and patchbay
    machine = Machine()
    patchbay = PatchBay()

    # Instantiate the subcircuit
    exposed_inputs, exposed_outputs = instantiate_subcircuit(
        subcircuit_def,
        "DOUBLE1",
        machine,
        patchbay,
    )

    # Verify inputs and outputs exist
    assert "in" in exposed_inputs
    assert "out" in exposed_outputs

    # Write to input, step, read output
    exposed_inputs["in"].write(5.0)
    patchbay.propagate()
    machine.step()

    # Output should be 5.0 * 2.0 = 10.0
    output_value = exposed_outputs["out"].read()
    assert abs(output_value - 10.0) < 1e-6


# =============================================================================
# Test 2: SubcircuitComponent Internal Wiring
# =============================================================================


def test_subcircuit_component_internal_wiring() -> None:
    """Create SubcircuitDef with two components and internal patch, verify signal flow."""
    # Create a subcircuit that patches two Coefficient components together
    # Input -> COEFF1 (k=2) -> COEFF2 (k=3) -> Output
    # Expected: 5.0 * 2 * 3 = 30.0

    coeff1_def = ComponentDef(name="COEFF1", type="Coefficient", params={"k": 2.0})
    coeff2_def = ComponentDef(name="COEFF2", type="Coefficient", params={"k": 3.0})

    # Internal patch: COEFF1.out -> COEFF2.in
    internal_patch = PatchDef(source="COEFF1.out", dest="COEFF2.in")

    subcircuit_def = SubcircuitDef(
        name="DoubleTriple",
        description="Multiply by 2 then by 3",
        inputs=["in"],
        outputs=["out"],
        components=[coeff1_def, coeff2_def],
        patches=[internal_patch],
        input_map={"in": "COEFF1.in"},
        output_map={"out": "COEFF2.out"},
    )

    # Create machine and patchbay
    machine = Machine()
    patchbay = PatchBay()

    # Instantiate the subcircuit
    exposed_inputs, exposed_outputs = instantiate_subcircuit(
        subcircuit_def,
        "CHAIN1",
        machine,
        patchbay,
    )

    # Write to input
    exposed_inputs["in"].write(5.0)

    # Step and propagate signals
    patchbay.propagate()
    machine.step()

    # Propagate again (to get COEFF2's output from COEFF1's output)
    patchbay.propagate()
    machine.step()

    # Output should be 5.0 * 2.0 * 3.0 = 30.0
    output_value = exposed_outputs["out"].read()
    assert abs(output_value - 30.0) < 1e-6


# =============================================================================
# Test 3: SubcircuitComponent Reset
# =============================================================================


def test_subcircuit_component_reset() -> None:
    """Create subcircuit with Integrator, run steps, reset, verify state cleared."""
    # Create a subcircuit with an Integrator
    integrator_def = ComponentDef(
        name="INT1",
        type="Integrator",
        params={"initial": 0.0, "gain": 1.0},
    )

    subcircuit_def = SubcircuitDef(
        name="IntegrationUnit",
        description="Integrate input signal",
        inputs=["in"],
        outputs=["out"],
        components=[integrator_def],
        input_map={"in": "INT1.in"},
        output_map={"out": "INT1.out"},
    )

    # Create machine and patchbay
    machine = Machine(dt=0.01)
    patchbay = PatchBay()

    # Instantiate the subcircuit
    exposed_inputs, exposed_outputs = instantiate_subcircuit(
        subcircuit_def,
        "INTEG1",
        machine,
        patchbay,
    )

    # Feed constant input and step several times
    exposed_inputs["in"].write(1.0)

    for _ in range(10):
        patchbay.propagate()
        machine.step()

    # State should have accumulated: 0 + 1.0 * 1.0 * (0.01 * 10) = 0.1
    output_before_reset = exposed_outputs["out"].read()
    assert output_before_reset > 0.05  # Some positive accumulation

    # Reset the machine
    machine.reset()

    # Output should be back to initial value (0.0)
    output_after_reset = exposed_outputs["out"].read()
    assert abs(output_after_reset - 0.0) < 1e-6


# =============================================================================
# Test 4: Subcircuit Registry Integration
# =============================================================================


def test_subcircuit_registry_integration() -> None:
    """Register subcircuit via register_subcircuit(), create via create_component()."""
    # Create a subcircuit definition
    coeff_def = ComponentDef(name="COEFF1", type="Coefficient", params={"k": 5.0})

    subcircuit_def = SubcircuitDef(
        name="RegistryTestSC",
        description="Multiply input by 5",
        inputs=["in"],
        outputs=["out"],
        components=[coeff_def],
        input_map={"in": "COEFF1.in"},
        output_map={"out": "COEFF1.out"},
    )

    # Register the subcircuit
    register_subcircuit("RegistryTestSC", subcircuit_def)

    # Verify it's in the SUBCIRCUITS registry
    assert "RegistryTestSC" in SUBCIRCUITS
    assert SUBCIRCUITS["RegistryTestSC"] is subcircuit_def

    # Create machine and patchbay
    machine = Machine()
    patchbay = PatchBay()

    # Create the component from the registry using create_component
    component = create_component(
        "RegistryTestSC",
        "RTEST1",
        params={"machine": machine, "patchbay": patchbay},
    )

    # Verify it's a SubcircuitComponent
    assert isinstance(component, SubcircuitComponent)
    assert component.name == "RTEST1"

    # Verify I/O works
    assert "in" in component.inputs
    assert "out" in component.outputs

    # Test signal flow
    component.inputs["in"].write(2.0)
    patchbay.propagate()
    machine.step()

    # Output should be 2.0 * 5.0 = 10.0
    output_value = component.outputs["out"].read()
    assert abs(output_value - 10.0) < 1e-6


# =============================================================================
# Test 5: List Component Types Includes Subcircuits
# =============================================================================


def test_list_component_types_includes_subcircuits() -> None:
    """Registered subcircuit appears in list_component_types()."""
    # Create and register a new subcircuit
    coeff_def = ComponentDef(name="COEFF1", type="Coefficient", params={"k": 1.0})

    subcircuit_def = SubcircuitDef(
        name="ListTestSC",
        description="Test subcircuit for list",
        inputs=["in"],
        outputs=["out"],
        components=[coeff_def],
        input_map={"in": "COEFF1.in"},
        output_map={"out": "COEFF1.out"},
    )

    # Register the subcircuit
    register_subcircuit("ListTestSC", subcircuit_def)

    # Get list of component types
    component_types = list_component_types()

    # Verify the registered subcircuit appears in the list
    assert "ListTestSC" in component_types

    # Verify some built-in components are also present
    assert "Coefficient" in component_types
    assert "Integrator" in component_types
    assert "Summer" in component_types
    assert "Multiplier" in component_types

    # Verify it's a sorted list
    assert component_types == sorted(component_types)


# =============================================================================
# Additional: Complex Subcircuit Test
# =============================================================================


def test_subcircuit_with_multiple_inputs() -> None:
    """Test subcircuit with multiple inputs and a Summer component."""
    # Create a subcircuit with two inputs that are summed
    # Input1 -> Summer, Input2 -> Summer, Summer.out -> Output

    summer_def = ComponentDef(
        name="SUM1",
        type="Summer",
        params={"weights": [1.0, 1.0]},
    )

    subcircuit_def = SubcircuitDef(
        name="Adder",
        description="Add two inputs",
        inputs=["in0", "in1"],
        outputs=["out"],
        components=[summer_def],
        input_map={"in0": "SUM1.in0", "in1": "SUM1.in1"},
        output_map={"out": "SUM1.out"},
    )

    # Create machine and patchbay
    machine = Machine()
    patchbay = PatchBay()

    # Instantiate the subcircuit
    exposed_inputs, exposed_outputs = instantiate_subcircuit(
        subcircuit_def,
        "ADD1",
        machine,
        patchbay,
    )

    # Write to both inputs
    exposed_inputs["in0"].write(3.0)
    exposed_inputs["in1"].write(4.0)

    # Step
    patchbay.propagate()
    machine.step()

    # Output should be 3.0 + 4.0 = 7.0
    output_value = exposed_outputs["out"].read()
    assert abs(output_value - 7.0) < 1e-6


# =============================================================================
# Additional: Error Handling Tests
# =============================================================================


def test_subcircuit_missing_input_mapping() -> None:
    """Test that missing input mapping raises appropriate error."""
    coeff_def = ComponentDef(name="COEFF1", type="Coefficient", params={"k": 2.0})

    # No input mapping and COEFF1 doesn't have a port named 'missing_input'
    subcircuit_def = SubcircuitDef(
        name="BadInputs",
        description="Missing input mapping",
        inputs=["missing_input"],
        outputs=["out"],
        components=[coeff_def],
        output_map={"out": "COEFF1.out"},
    )

    machine = Machine()
    patchbay = PatchBay()

    # Should raise ValueError due to missing input mapping
    with pytest.raises(ValueError, match="Could not find input port"):
        instantiate_subcircuit(subcircuit_def, "INSTANCE1", machine, patchbay)


def test_subcircuit_missing_output_mapping() -> None:
    """Test that missing output mapping raises appropriate error."""
    coeff_def = ComponentDef(name="COEFF1", type="Coefficient", params={"k": 2.0})

    # No output mapping and COEFF1 doesn't have a port named 'missing_output'
    subcircuit_def = SubcircuitDef(
        name="BadOutputs",
        description="Missing output mapping",
        inputs=["in"],
        outputs=["missing_output"],
        components=[coeff_def],
        input_map={"in": "COEFF1.in"},
    )

    machine = Machine()
    patchbay = PatchBay()

    # Should raise ValueError due to missing output mapping
    with pytest.raises(ValueError, match="Could not find output port"):
        instantiate_subcircuit(subcircuit_def, "INSTANCE1", machine, patchbay)


def test_subcircuit_invalid_port_reference() -> None:
    """Test that invalid port references in patches raise errors."""
    coeff1_def = ComponentDef(name="COEFF1", type="Coefficient", params={"k": 2.0})
    coeff2_def = ComponentDef(name="COEFF2", type="Coefficient", params={"k": 3.0})

    # Invalid output port name
    invalid_patch = PatchDef(source="COEFF1.invalid_port", dest="COEFF2.in")

    subcircuit_def = SubcircuitDef(
        name="BadPatch",
        description="Invalid patch",
        inputs=["in"],
        outputs=["out"],
        components=[coeff1_def, coeff2_def],
        patches=[invalid_patch],
        input_map={"in": "COEFF1.in"},
        output_map={"out": "COEFF2.out"},
    )

    machine = Machine()
    patchbay = PatchBay()

    # Should raise ValueError due to invalid port reference
    with pytest.raises(ValueError, match="has no output port"):
        instantiate_subcircuit(subcircuit_def, "INSTANCE1", machine, patchbay)


# =============================================================================
# Additional: PatchDef from_list conversion test
# =============================================================================


def test_patchdef_from_list() -> None:
    """Test PatchDef.from_list() factory method."""
    patch_list = ["COEFF1.out", "COEFF2.in"]
    patch_def = PatchDef.from_list(patch_list)

    assert patch_def.source == "COEFF1.out"
    assert patch_def.dest == "COEFF2.in"


def test_patchdef_from_list_invalid() -> None:
    """Test PatchDef.from_list() with invalid input."""
    # Should raise ValueError for list with wrong number of elements
    with pytest.raises(ValueError, match="exactly 2 elements"):
        PatchDef.from_list(["COEFF1.out"])

    with pytest.raises(ValueError, match="exactly 2 elements"):
        PatchDef.from_list(["COEFF1.out", "COEFF2.in", "EXTRA"])


# =============================================================================
# Additional: SubcircuitDef.from_dict() test
# =============================================================================


def test_subcircuit_def_from_dict() -> None:
    """Test SubcircuitDef.from_dict() handles various input formats."""
    data = {
        "name": "TestCircuit",
        "description": "A test subcircuit",
        "inputs": ["in"],
        "outputs": ["out"],
        "components": [
            {"name": "COEFF1", "type": "Coefficient", "params": {"k": 2.0}},
        ],
        "patches": [
            ["COEFF1.out", "COEFF2.in"],  # List format
        ],
        "input_map": {"in": "COEFF1.in"},
        "output_map": {"out": "COEFF1.out"},
    }

    subcircuit_def = SubcircuitDef.from_dict(data)

    assert subcircuit_def.name == "TestCircuit"
    assert len(subcircuit_def.components) == 1
    assert subcircuit_def.components[0].type == "Coefficient"
    assert len(subcircuit_def.patches) == 1
    assert subcircuit_def.patches[0].source == "COEFF1.out"
    assert subcircuit_def.patches[0].dest == "COEFF2.in"


# =============================================================================
# Additional: Softmax Subcircuit Test
# =============================================================================


def test_softmax_subcircuit() -> None:
    """Softmax subcircuit computes correct normalized outputs."""
    import math
    from engine.subcircuits.softmax import register_softmax
    from engine.registry import is_subcircuit

    # Register softmax if not already registered
    if not is_subcircuit("Softmax"):
        register_softmax()

    machine = Machine()
    patchbay = PatchBay()

    sm = create_component("Softmax", "SM1", {"machine": machine, "patchbay": patchbay})

    # Test softmax([1, 2])
    sm.inputs["in0"].write(1.0)
    sm.inputs["in1"].write(2.0)

    # Run multiple cycles for pipeline to settle
    for _ in range(3):
        patchbay.propagate()
        machine.step()
    patchbay.propagate()

    out0 = sm.outputs["out0"].read()
    out1 = sm.outputs["out1"].read()

    # Expected: softmax([1,2]) = [e^1/(e^1+e^2), e^2/(e^1+e^2)]
    expected0 = math.exp(1) / (math.exp(1) + math.exp(2))
    expected1 = math.exp(2) / (math.exp(1) + math.exp(2))

    assert abs(out0 - expected0) < 0.001
    assert abs(out1 - expected1) < 0.001
    assert abs(out0 + out1 - 1.0) < 0.001  # Should sum to 1
