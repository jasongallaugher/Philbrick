"""Tests for Summer and Coefficient components."""

import pytest
from engine.components.math import Summer, Coefficient, Inverter


def test_summer_two_inputs() -> None:
    """Summer with two inputs and default weights [1.0, 1.0]."""
    summer = Summer("SUM1")

    # Feed inputs
    summer.inputs["in0"].write(3.0)
    summer.inputs["in1"].write(4.0)

    # Step to compute output
    summer.step(0.1)

    # Output should be 3.0 + 4.0 = 7.0
    assert abs(summer.outputs["out"].read() - 7.0) < 1e-6


def test_summer_weighted() -> None:
    """Summer with weights [2.0, 0.5] computes weighted sum."""
    summer = Summer("SUM1", weights=[2.0, 0.5])

    # Feed inputs
    summer.inputs["in0"].write(3.0)
    summer.inputs["in1"].write(4.0)

    # Step to compute output
    summer.step(0.1)

    # Output should be 3.0*2.0 + 4.0*0.5 = 6.0 + 2.0 = 8.0
    assert abs(summer.outputs["out"].read() - 8.0) < 1e-6


def test_summer_three_inputs() -> None:
    """Summer with three inputs verifies all contribute."""
    summer = Summer("SUM1", weights=[1.0, 2.0, 3.0])

    # Feed all three inputs
    summer.inputs["in0"].write(1.0)
    summer.inputs["in1"].write(2.0)
    summer.inputs["in2"].write(3.0)

    # Step to compute output
    summer.step(0.1)

    # Output should be 1.0*1.0 + 2.0*2.0 + 3.0*3.0 = 1.0 + 4.0 + 9.0 = 14.0
    assert abs(summer.outputs["out"].read() - 14.0) < 1e-6


def test_summer_reset() -> None:
    """Summer reset clears output to 0."""
    summer = Summer("SUM1")

    # Feed inputs and compute
    summer.inputs["in0"].write(3.0)
    summer.inputs["in1"].write(4.0)
    summer.step(0.1)

    # Output should be 7.0
    assert abs(summer.outputs["out"].read() - 7.0) < 1e-6

    # Reset should clear output to 0
    summer.reset()
    assert abs(summer.outputs["out"].read() - 0.0) < 1e-6


def test_coefficient_multiply() -> None:
    """Coefficient multiplies input by k."""
    coeff = Coefficient("COEF1", k=2.0)

    # Feed input
    coeff.inputs["in"].write(5.0)

    # Step to compute output
    coeff.step(0.1)

    # Output should be 5.0 * 2.0 = 10.0
    assert abs(coeff.outputs["out"].read() - 10.0) < 1e-6


def test_coefficient_default() -> None:
    """Coefficient with default k=1.0 passes through unchanged."""
    coeff = Coefficient("COEF1")

    # Feed input
    coeff.inputs["in"].write(5.0)

    # Step to compute output
    coeff.step(0.1)

    # Output should be 5.0 * 1.0 = 5.0
    assert abs(coeff.outputs["out"].read() - 5.0) < 1e-6


def test_coefficient_negative() -> None:
    """Coefficient with k=-1.0 inverts sign."""
    coeff = Coefficient("COEF1", k=-1.0)

    # Feed input
    coeff.inputs["in"].write(5.0)

    # Step to compute output
    coeff.step(0.1)

    # Output should be 5.0 * -1.0 = -5.0
    assert abs(coeff.outputs["out"].read() - (-5.0)) < 1e-6


def test_coefficient_reset() -> None:
    """Coefficient reset clears output to 0."""
    coeff = Coefficient("COEF1", k=2.0)

    # Feed input and compute
    coeff.inputs["in"].write(5.0)
    coeff.step(0.1)

    # Output should be 10.0
    assert abs(coeff.outputs["out"].read() - 10.0) < 1e-6

    # Reset should clear output to 0
    coeff.reset()
    assert abs(coeff.outputs["out"].read() - 0.0) < 1e-6


def test_inverter_positive() -> None:
    """Inverter inverts positive input."""
    inv = Inverter("INV1")

    # Feed positive input
    inv.inputs["in"].write(5.0)

    # Step to compute output
    inv.step(0.1)

    # Output should be -5.0
    assert abs(inv.outputs["out"].read() - (-5.0)) < 1e-6


def test_inverter_negative() -> None:
    """Inverter inverts negative input."""
    inv = Inverter("INV1")

    # Feed negative input
    inv.inputs["in"].write(-3.0)

    # Step to compute output
    inv.step(0.1)

    # Output should be 3.0
    assert abs(inv.outputs["out"].read() - 3.0) < 1e-6


def test_inverter_zero() -> None:
    """Inverter handles zero input."""
    inv = Inverter("INV1")

    # Feed zero input
    inv.inputs["in"].write(0.0)

    # Step to compute output
    inv.step(0.1)

    # Output should be 0.0
    assert abs(inv.outputs["out"].read() - 0.0) < 1e-6


def test_inverter_reset() -> None:
    """Inverter reset clears output to 0."""
    inv = Inverter("INV1")

    # Feed input and compute
    inv.inputs["in"].write(5.0)
    inv.step(0.1)

    # Output should be -5.0
    assert abs(inv.outputs["out"].read() - (-5.0)) < 1e-6

    # Reset should clear output to 0
    inv.reset()
    assert abs(inv.outputs["out"].read() - 0.0) < 1e-6
