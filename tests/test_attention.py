"""Tests for attention primitives: Exp, Divider, DotProduct, and Max."""

import math
import pytest
from engine.components.math import Exp, Divider, DotProduct, Max


# =============================================================================
# Exp Tests
# =============================================================================


def test_exp_basic() -> None:
    """Exp computes exponential: exp(0) = 1, exp(1) ≈ 2.718."""
    exp = Exp("EXP1")

    # Test exp(0) = 1
    exp.inputs["in"].write(0.0)
    exp.step(0.1)
    assert abs(exp.outputs["out"].read() - 1.0) < 1e-6

    # Test exp(1) ≈ 2.718
    exp.inputs["in"].write(1.0)
    exp.step(0.1)
    expected = math.exp(1.0)
    assert abs(exp.outputs["out"].read() - expected) < 1e-6


def test_exp_scale() -> None:
    """Exp with scale factor: scale=2 means exp(1*2) = exp(2)."""
    exp = Exp("EXP1", scale=2.0)

    # Feed input 1.0 with scale 2.0
    exp.inputs["in"].write(1.0)
    exp.step(0.1)

    # Output should be exp(1.0 * 2.0) = exp(2.0)
    expected = math.exp(2.0)
    assert abs(exp.outputs["out"].read() - expected) < 1e-6


def test_exp_clamp() -> None:
    """Exp clamps large inputs to avoid overflow (input=100 gets clamped)."""
    exp = Exp("EXP1")

    # Feed a large input that would overflow without clamping
    exp.inputs["in"].write(100.0)
    exp.step(0.1)

    # Output should be exp(10.0) due to clamping to max 10.0
    # Should not overflow/raise exception
    result = exp.outputs["out"].read()
    expected = math.exp(10.0)
    assert abs(result - expected) < 1e-6
    assert not math.isnan(result) and not math.isinf(result)


# =============================================================================
# Divider Tests
# =============================================================================


def test_divider_basic() -> None:
    """Divider computes division: 6/2 = 3."""
    div = Divider("DIV1")

    # Feed inputs
    div.inputs["num"].write(6.0)
    div.inputs["den"].write(2.0)

    # Step to compute output
    div.step(0.1)

    # Output should be 6.0 / 2.0 = 3.0
    assert abs(div.outputs["out"].read() - 3.0) < 1e-6


def test_divider_negative_denominator() -> None:
    """Divider handles negative denominator: 6/-2 = -3."""
    div = Divider("DIV1")

    # Feed inputs with negative denominator
    div.inputs["num"].write(6.0)
    div.inputs["den"].write(-2.0)

    # Step to compute output
    div.step(0.1)

    # Output should be 6.0 / -2.0 = -3.0
    assert abs(div.outputs["out"].read() - (-3.0)) < 1e-6


def test_divider_small_denominator() -> None:
    """Divider uses epsilon to avoid division by zero."""
    div = Divider("DIV1", epsilon=1e-6)

    # Feed very small denominator
    div.inputs["num"].write(1.0)
    div.inputs["den"].write(1e-8)  # Smaller than epsilon

    # Step to compute output
    div.step(0.1)

    # Output should use epsilon to avoid division by zero
    # Denominator becomes max(abs(1e-8), 1e-6) = 1e-6
    expected = 1.0 / 1e-6
    assert abs(div.outputs["out"].read() - expected) < 1e-3


# =============================================================================
# DotProduct Tests
# =============================================================================


def test_dot_product_basic() -> None:
    """DotProduct computes dot product: [1,2]*[3,4] = 3+8 = 11."""
    dot = DotProduct("DOT1", size=2)

    # Feed vector a: [1, 2]
    dot.inputs["a0"].write(1.0)
    dot.inputs["a1"].write(2.0)

    # Feed vector b: [3, 4]
    dot.inputs["b0"].write(3.0)
    dot.inputs["b1"].write(4.0)

    # Step to compute output
    dot.step(0.1)

    # Output should be 1*3 + 2*4 = 3 + 8 = 11
    assert abs(dot.outputs["out"].read() - 11.0) < 1e-6


def test_dot_product_size() -> None:
    """DotProduct with size=2 only uses first 2 elements."""
    dot = DotProduct("DOT1", size=2)

    # Feed vector a: [1, 2]
    dot.inputs["a0"].write(1.0)
    dot.inputs["a1"].write(2.0)

    # Feed vector b: [3, 4]
    dot.inputs["b0"].write(3.0)
    dot.inputs["b1"].write(4.0)

    # Step to compute output
    dot.step(0.1)

    # Output should be 1*3 + 2*4 = 11 (size constraint respected)
    assert abs(dot.outputs["out"].read() - 11.0) < 1e-6


# =============================================================================
# Max Tests
# =============================================================================


def test_max_basic() -> None:
    """Max returns maximum of inputs: max(3, 7) = 7."""
    max_comp = Max("MAX1", size=2)

    # Feed inputs
    max_comp.inputs["in0"].write(3.0)
    max_comp.inputs["in1"].write(7.0)

    # Step to compute output
    max_comp.step(0.1)

    # Output should be 7.0
    assert abs(max_comp.outputs["out"].read() - 7.0) < 1e-6


def test_max_size() -> None:
    """Max with size=3 finds maximum of 3 inputs."""
    max_comp = Max("MAX1", size=3)

    # Feed 3 inputs: [5, 2, 9]
    max_comp.inputs["in0"].write(5.0)
    max_comp.inputs["in1"].write(2.0)
    max_comp.inputs["in2"].write(9.0)

    # Step to compute output
    max_comp.step(0.1)

    # Output should be 9.0 (maximum of 5, 2, 9)
    assert abs(max_comp.outputs["out"].read() - 9.0) < 1e-6
