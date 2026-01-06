"""Tests for Integrator component."""

import pytest
from engine.components.integrator import Integrator


def test_integrator_constant_input() -> None:
    """Integrator with constant input climbs linearly."""
    integrator = Integrator("INT1")

    # Feed constant 1.0 input
    integrator.inputs["in"].write(1.0)

    # Initial output should be 0.0
    assert abs(integrator.outputs["out"].read() - 0.0) < 1e-6

    # Step with dt=1.0, output should be 1.0 (integral of 1 over 1 second)
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 1.0) < 1e-6

    # Step again, output should be 2.0
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 2.0) < 1e-6

    # Step again, output should be 3.0
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 3.0) < 1e-6


def test_integrator_initial_condition() -> None:
    """Integrator starts at initial value and accumulates from there."""
    integrator = Integrator("INT1", initial=5.0)

    # Output should start at initial value
    assert abs(integrator.outputs["out"].read() - 5.0) < 1e-6

    # Feed constant 1.0 input
    integrator.inputs["in"].write(1.0)

    # After step with dt=1.0, should be 6.0 (5.0 + 1.0)
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 6.0) < 1e-6

    # After another step, should be 7.0
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 7.0) < 1e-6


def test_integrator_gain() -> None:
    """Integrator with gain multiplies the integration rate."""
    integrator = Integrator("INT1", gain=2.0)

    # Feed constant 1.0 input
    integrator.inputs["in"].write(1.0)

    # With gain=2.0, output climbs at 2x rate
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 2.0) < 1e-6

    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 4.0) < 1e-6

    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 6.0) < 1e-6


def test_integrator_reset() -> None:
    """Integrator reset restores state to initial value."""
    integrator = Integrator("INT1", initial=5.0)

    # Feed input and accumulate state
    integrator.inputs["in"].write(1.0)
    integrator.step(1.0)
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 7.0) < 1e-6

    # Reset should restore to initial value
    integrator.reset()
    assert abs(integrator.outputs["out"].read() - 5.0) < 1e-6

    # After reset, integration should resume from initial
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 6.0) < 1e-6


def test_integrator_zero_input() -> None:
    """Integrator with zero input holds its state."""
    integrator = Integrator("INT1", initial=3.0)

    # Feed zero input
    integrator.inputs["in"].write(0.0)

    # State should not change
    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 3.0) < 1e-6

    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 3.0) < 1e-6

    integrator.step(1.0)
    assert abs(integrator.outputs["out"].read() - 3.0) < 1e-6
