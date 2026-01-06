"""Tests for Phase 3 components: Multiplier, Comparator, and Limiter."""

import pytest
from engine.components.math import Multiplier, Comparator, Limiter


# =============================================================================
# Multiplier Tests
# =============================================================================


def test_multiplier_basic() -> None:
    """Multiplier computes product of two inputs: 2 * 3 = 6."""
    mult = Multiplier("MULT1")

    # Feed inputs
    mult.inputs["x"].write(2.0)
    mult.inputs["y"].write(3.0)

    # Step to compute output
    mult.step(0.1)

    # Output should be 2.0 * 3.0 = 6.0
    assert abs(mult.outputs["out"].read() - 6.0) < 1e-6


def test_multiplier_negative() -> None:
    """Multiplier handles negative inputs: -2 * 3 = -6."""
    mult = Multiplier("MULT1")

    # Feed inputs with one negative
    mult.inputs["x"].write(-2.0)
    mult.inputs["y"].write(3.0)

    # Step to compute output
    mult.step(0.1)

    # Output should be -2.0 * 3.0 = -6.0
    assert abs(mult.outputs["out"].read() - (-6.0)) < 1e-6


def test_multiplier_with_scale() -> None:
    """Multiplier with scale factor: 2 * 3 * 0.5 = 3."""
    mult = Multiplier("MULT1", scale=0.5)

    # Feed inputs
    mult.inputs["x"].write(2.0)
    mult.inputs["y"].write(3.0)

    # Step to compute output
    mult.step(0.1)

    # Output should be 2.0 * 3.0 * 0.5 = 3.0
    assert abs(mult.outputs["out"].read() - 3.0) < 1e-6


def test_multiplier_reset() -> None:
    """Multiplier reset clears output to 0."""
    mult = Multiplier("MULT1")

    # Feed inputs and compute
    mult.inputs["x"].write(2.0)
    mult.inputs["y"].write(3.0)
    mult.step(0.1)

    # Output should be 6.0
    assert abs(mult.outputs["out"].read() - 6.0) < 1e-6

    # Reset should clear output to 0
    mult.reset()
    assert abs(mult.outputs["out"].read() - 0.0) < 1e-6


# =============================================================================
# Comparator Tests
# =============================================================================


def test_comparator_above_threshold() -> None:
    """Comparator returns high when input > threshold."""
    comp = Comparator("COMP1")

    # Feed input above default threshold (0.0)
    comp.inputs["in"].write(1.0)

    # Step to compute output
    comp.step(0.1)

    # Output should be high (default 1.0)
    assert abs(comp.outputs["out"].read() - 1.0) < 1e-6


def test_comparator_below_threshold() -> None:
    """Comparator returns low when input < threshold."""
    comp = Comparator("COMP1")

    # Feed input below default threshold (0.0)
    comp.inputs["in"].write(-1.0)

    # Step to compute output
    comp.step(0.1)

    # Output should be low (default -1.0)
    assert abs(comp.outputs["out"].read() - (-1.0)) < 1e-6


def test_comparator_at_threshold() -> None:
    """Comparator returns high when input == threshold."""
    comp = Comparator("COMP1")

    # Feed input equal to default threshold (0.0)
    comp.inputs["in"].write(0.0)

    # Step to compute output
    comp.step(0.1)

    # Output should be high (default 1.0) when at threshold
    assert abs(comp.outputs["out"].read() - 1.0) < 1e-6


def test_comparator_custom_values() -> None:
    """Comparator with custom threshold, high, and low values."""
    comp = Comparator("COMP1", threshold=5.0, high=10.0, low=0.0)

    # Test above threshold
    comp.inputs["in"].write(6.0)
    comp.step(0.1)
    assert abs(comp.outputs["out"].read() - 10.0) < 1e-6

    # Test below threshold
    comp.inputs["in"].write(4.0)
    comp.step(0.1)
    assert abs(comp.outputs["out"].read() - 0.0) < 1e-6


# =============================================================================
# Limiter Tests
# =============================================================================


def test_limiter_within_range() -> None:
    """Limiter passes through values within range unchanged."""
    lim = Limiter("LIM1")

    # Feed input within default range (-1.0 to 1.0)
    lim.inputs["in"].write(0.5)

    # Step to compute output
    lim.step(0.1)

    # Output should be 0.5 (unchanged)
    assert abs(lim.outputs["out"].read() - 0.5) < 1e-6


def test_limiter_above_max() -> None:
    """Limiter clamps values above max to max."""
    lim = Limiter("LIM1")

    # Feed input above default max (1.0)
    lim.inputs["in"].write(2.0)

    # Step to compute output
    lim.step(0.1)

    # Output should be clamped to 1.0
    assert abs(lim.outputs["out"].read() - 1.0) < 1e-6


def test_limiter_below_min() -> None:
    """Limiter clamps values below min to min."""
    lim = Limiter("LIM1")

    # Feed input below default min (-1.0)
    lim.inputs["in"].write(-2.0)

    # Step to compute output
    lim.step(0.1)

    # Output should be clamped to -1.0
    assert abs(lim.outputs["out"].read() - (-1.0)) < 1e-6


def test_limiter_custom_range() -> None:
    """Limiter with custom min/max range."""
    lim = Limiter("LIM1", min_val=0.0, max_val=10.0)

    # Test within range
    lim.inputs["in"].write(5.0)
    lim.step(0.1)
    assert abs(lim.outputs["out"].read() - 5.0) < 1e-6

    # Test above max
    lim.inputs["in"].write(15.0)
    lim.step(0.1)
    assert abs(lim.outputs["out"].read() - 10.0) < 1e-6

    # Test below min
    lim.inputs["in"].write(-5.0)
    lim.step(0.1)
    assert abs(lim.outputs["out"].read() - 0.0) < 1e-6
