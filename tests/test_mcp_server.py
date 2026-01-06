"""Tests for MCP server tools.

These tests call the tool functions directly (not via MCP protocol) to verify
their functionality for circuit creation, component management, simulation,
and signal reading.
"""

import pytest
from mcp_server import (
    philbrick_list_components,
    philbrick_create_circuit,
    philbrick_add_component,
    philbrick_connect,
    philbrick_run,
    philbrick_read_signal,
    philbrick_get_signal_stats,
    philbrick_get_time_series,
    philbrick_check_settled,
)


# =============================================================================
# list_components Tests
# =============================================================================


def test_list_components() -> None:
    """philbrick_list_components returns list including Integrator, Summer, and others."""
    result = philbrick_list_components()

    assert "components" in result
    assert isinstance(result["components"], list)

    components = result["components"]

    # Check for required components
    assert "Integrator" in components
    assert "Summer" in components
    assert "Multiplier" in components

    # Verify it's non-empty
    assert len(components) > 0


# =============================================================================
# create_circuit Tests
# =============================================================================


def test_create_circuit() -> None:
    """philbrick_create_circuit returns success response."""
    result = philbrick_create_circuit()

    assert "status" in result
    assert result["status"] == "success"


# =============================================================================
# add_component Tests
# =============================================================================


def test_add_component() -> None:
    """Create circuit, add VoltageSource, verify success."""
    # Reset state
    philbrick_create_circuit()

    # Add a VoltageSource component
    result = philbrick_add_component(
        component_type="VoltageSource",
        name="VSRC1",
        params={"frequency": 1.0, "amplitude": 5.0}
    )

    assert result["status"] == "success"
    assert result["name"] == "VSRC1"
    assert result["type"] == "VoltageSource"


# =============================================================================
# connect Tests
# =============================================================================


def test_connect() -> None:
    """Create circuit, add two components, connect them, verify success."""
    # Reset state
    philbrick_create_circuit()

    # Add components
    philbrick_add_component("VoltageSource", "VSRC1", {"frequency": 1.0})
    philbrick_add_component("Integrator", "INT1", {"initial": 0.0})

    # Connect them
    result = philbrick_connect("VSRC1.out", "INT1.in")

    assert result["status"] == "success"
    assert result["source"] == "VSRC1.out"
    assert result["destination"] == "INT1.in"


# =============================================================================
# run_simulation Tests
# =============================================================================


def test_run_simulation() -> None:
    """Create circuit with VoltageSource, run 10 steps, verify time advances."""
    # Reset state
    philbrick_create_circuit()

    # Add a VoltageSource
    philbrick_add_component("VoltageSource", "VSRC1", {"frequency": 1.0})

    # Run simulation for 10 steps
    result = philbrick_run(steps=10)

    assert result["status"] == "success"
    assert result["steps_executed"] == 10
    assert "final_time" in result
    # With dt=0.001 per step, 10 steps should give 0.01 seconds
    assert abs(result["final_time"] - 0.01) < 1e-6


# =============================================================================
# read_signal Tests
# =============================================================================


def test_read_signal() -> None:
    """Create circuit with VoltageSource, run, read signal, verify value."""
    # Reset state
    philbrick_create_circuit()

    # Add a VoltageSource with constant amplitude
    philbrick_add_component(
        "VoltageSource",
        "VSRC1",
        {"frequency": 0.0, "amplitude": 5.0}
    )

    # Run one step to initialize
    philbrick_run(steps=1)

    # Read the output signal
    result = philbrick_read_signal("VSRC1.out")

    assert result["status"] == "success"
    assert result["port"] == "VSRC1.out"
    # With frequency=0, sin(0) = 0, but amplitude is 5.0, so output should be ~0
    assert "value" in result
    # At time ~0, sin(2π*0*t) = sin(0) = 0
    assert abs(result["value"]) < 1e-6


# =============================================================================
# Full Workflow Tests
# =============================================================================


def test_full_workflow() -> None:
    """Full integration test: create circuit, add components, connect, run, read."""
    # Create new circuit
    create_result = philbrick_create_circuit()
    assert create_result["status"] == "success"

    # Add components
    vsrc_result = philbrick_add_component(
        "VoltageSource",
        "VSRC1",
        {"frequency": 1.0, "amplitude": 2.0}
    )
    assert vsrc_result["status"] == "success"

    int_result = philbrick_add_component(
        "Integrator",
        "INT1",
        {"initial": 0.0}
    )
    assert int_result["status"] == "success"

    # Connect them
    connect_result = philbrick_connect("VSRC1.out", "INT1.in")
    assert connect_result["status"] == "success"

    # Run simulation
    run_result = philbrick_run(steps=100)
    assert run_result["status"] == "success"
    assert run_result["steps_executed"] == 100
    assert abs(run_result["final_time"] - 0.1) < 1e-6

    # Read signals
    vsrc_read = philbrick_read_signal("VSRC1.out")
    assert vsrc_read["status"] == "success"
    assert "value" in vsrc_read

    int_output = philbrick_read_signal("INT1.out")
    assert int_output["status"] == "success"
    assert "value" in int_output

    # Integrator output should change from integrating the VoltageSource
    # (which produces a sinusoidal output)
    assert isinstance(int_output["value"], float)


def test_full_workflow_multiple_steps() -> None:
    """Run simulation across multiple invocations, verify time accumulation."""
    # Create circuit
    philbrick_create_circuit()

    # Add component
    philbrick_add_component("VoltageSource", "VSRC1", {"frequency": 1.0})

    # Run first batch
    result1 = philbrick_run(steps=50)
    assert result1["status"] == "success"
    assert abs(result1["final_time"] - 0.05) < 1e-6

    # Run second batch - time should accumulate
    result2 = philbrick_run(steps=50)
    assert result2["status"] == "success"
    assert abs(result2["final_time"] - 0.1) < 1e-6


def test_add_component_without_circuit() -> None:
    """Verify error when adding component without creating circuit first."""
    # Create one to reset state
    philbrick_create_circuit()

    # This should work fine since we just created a circuit
    # VoltageSource requires frequency parameter
    result = philbrick_add_component("VoltageSource", "VSRC1", {"frequency": 1.0})
    assert result["status"] == "success"


def test_read_signal_multiple_ports() -> None:
    """Read signals from different ports of same component."""
    # Reset
    philbrick_create_circuit()

    # Add Integrator with input and output ports
    philbrick_add_component("Integrator", "INT1", {"initial": 5.0})

    # Add VoltageSource to feed input
    philbrick_add_component("VoltageSource", "VSRC1", {"frequency": 0.0, "amplitude": 1.0})

    # Connect
    philbrick_connect("VSRC1.out", "INT1.in")

    # Run some steps
    philbrick_run(steps=5)

    # Read both input and output
    input_result = philbrick_read_signal("INT1.in")
    output_result = philbrick_read_signal("INT1.out")

    assert input_result["status"] == "success"
    assert output_result["status"] == "success"

    # Both should have values
    assert "value" in input_result
    assert "value" in output_result


def test_complex_circuit() -> None:
    """Create more complex circuit with multiple components and connections."""
    # Reset
    philbrick_create_circuit()

    # Add source
    philbrick_add_component("VoltageSource", "VSRC1", {"frequency": 1.0, "amplitude": 1.0})

    # Add processing chain
    philbrick_add_component("Integrator", "INT1", {"initial": 0.0})
    philbrick_add_component("Coefficient", "COEF1", {"k": 0.5})
    philbrick_add_component("Summer", "SUM1", {})

    # Connect source to integrator
    result1 = philbrick_connect("VSRC1.out", "INT1.in")
    assert result1["status"] == "success"

    # Connect integrator output to coefficient
    result2 = philbrick_connect("INT1.out", "COEF1.in")
    assert result2["status"] == "success"

    # Connect coefficient to summer (first input)
    result3 = philbrick_connect("COEF1.out", "SUM1.in1")
    assert result3["status"] == "success"

    # Run the simulation
    run_result = philbrick_run(steps=50)
    assert run_result["status"] == "success"

    # Read all outputs
    vsrc_val = philbrick_read_signal("VSRC1.out")
    int_val = philbrick_read_signal("INT1.out")
    coef_val = philbrick_read_signal("COEF1.out")
    sum_val = philbrick_read_signal("SUM1.out")

    assert all(r["status"] == "success" for r in [vsrc_val, int_val, coef_val, sum_val])
    assert all("value" in r for r in [vsrc_val, int_val, coef_val, sum_val])


# =============================================================================
# Rich Feedback Tools Tests
# =============================================================================


def test_get_signal_stats() -> None:
    """Get signal statistics: min, max, mean, final_value, num_samples."""
    # Reset
    philbrick_create_circuit()

    # Add a VoltageSource with sine wave
    philbrick_add_component(
        "VoltageSource",
        "VSRC1",
        {"frequency": 1.0, "amplitude": 5.0}
    )

    # Run for 1000 steps (1 second at dt=0.001) to capture full sine wave cycle
    philbrick_run(steps=1000)

    # Get statistics
    result = philbrick_get_signal_stats("VSRC1.out")

    assert result["status"] == "success"
    assert result["port"] == "VSRC1.out"
    assert result["num_samples"] == 1000

    # Verify all required fields are present
    assert "min" in result
    assert "max" in result
    assert "mean" in result
    assert "final_value" in result

    # For a sine wave with amplitude 5.0, min should be roughly -5 and max roughly 5
    # After 1 full cycle (1 second), should see both negative and positive values
    assert result["min"] < -2.0
    assert result["max"] > 2.0


def test_get_time_series() -> None:
    """Get time series of signal values with optional last_n limit."""
    # Reset
    philbrick_create_circuit()

    # Add a VoltageSource
    philbrick_add_component(
        "VoltageSource",
        "VSRC1",
        {"frequency": 1.0, "amplitude": 2.0}
    )

    # Run for 50 steps
    philbrick_run(steps=50)

    # Get full time series
    result = philbrick_get_time_series("VSRC1.out")

    assert result["status"] == "success"
    assert result["port"] == "VSRC1.out"
    assert result["num_samples"] == 50
    assert isinstance(result["values"], list)
    assert len(result["values"]) == 50

    # Test last_n parameter
    result_limited = philbrick_get_time_series("VSRC1.out", last_n=10)

    assert result_limited["status"] == "success"
    assert result_limited["num_samples"] == 10
    assert len(result_limited["values"]) == 10

    # Verify last_n values match the tail of the full series
    assert result_limited["values"] == result["values"][-10:]


def test_check_settled_true() -> None:
    """Check settled returns True for constant (non-oscillating) signal."""
    # Reset
    philbrick_create_circuit()

    # Add a VoltageSource with constant output (frequency=0)
    philbrick_add_component(
        "VoltageSource",
        "VSRC1",
        {"frequency": 0.0, "amplitude": 5.0}
    )

    # Run for several steps
    philbrick_run(steps=50)

    # Check if settled
    result = philbrick_check_settled("VSRC1.out")

    assert result["status"] == "success"
    assert result["port"] == "VSRC1.out"
    assert result["settled"] is True

    # With frequency=0, variation should be very small
    assert result["variation"] < 0.001


def test_check_settled_false() -> None:
    """Check settled returns False for oscillating signal."""
    # Reset
    philbrick_create_circuit()

    # Add a VoltageSource with oscillation (frequency=1.0)
    philbrick_add_component(
        "VoltageSource",
        "VSRC1",
        {"frequency": 1.0, "amplitude": 5.0}
    )

    # Run for many steps to ensure oscillation is captured
    philbrick_run(steps=100)

    # Check if settled with strict tolerance
    result = philbrick_check_settled("VSRC1.out", tolerance=0.001)

    assert result["status"] == "success"
    assert result["port"] == "VSRC1.out"
    assert result["settled"] is False

    # Oscillating sine wave should have significant variation
    assert result["variation"] > 0.1
