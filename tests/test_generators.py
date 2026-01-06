"""Tests for generator components: TriangleWave, SawtoothWave, SquareWave, and PiecewiseLinear."""

import pytest
from engine.components.generators import (
    TriangleWave,
    SawtoothWave,
    SquareWave,
    PiecewiseLinear,
)


# =============================================================================
# TriangleWave Tests
# =============================================================================


def test_triangle_wave_frequency() -> None:
    """Triangle wave reaches peak after 0.5/frequency seconds."""
    frequency = 4.0  # 4 Hz
    tri = TriangleWave("TRI1", frequency=frequency, amplitude=1.0)

    # At t=0, output is at -amplitude
    tri.step(0.0)
    assert abs(tri.outputs["out"].read() - (-1.0)) < 1e-6

    # After 0.5/frequency = 0.125 seconds, should be at peak (+amplitude)
    # This is when phase reaches 0.5 (halfway through rise in triangle)
    time_to_peak = 0.5 / frequency
    tri.step(time_to_peak)

    assert abs(tri.outputs["out"].read() - 1.0) < 1e-6


def test_triangle_wave_full_cycle() -> None:
    """Triangle wave returns to start after one full cycle."""
    frequency = 2.0  # 2 Hz
    tri = TriangleWave("TRI1", frequency=frequency, amplitude=1.0)

    # Get initial output
    tri.step(0.0)
    initial_output = tri.outputs["out"].read()

    # Advance by one full cycle: 1/frequency seconds
    cycle_time = 1.0 / frequency
    tri.step(cycle_time)

    final_output = tri.outputs["out"].read()
    assert abs(final_output - initial_output) < 1e-6


def test_triangle_wave_amplitude() -> None:
    """Triangle wave respects amplitude parameter."""
    frequency = 1.0
    amplitude = 2.5
    tri = TriangleWave("TRI1", frequency=frequency, amplitude=amplitude)

    # After 0.5 seconds at 1 Hz, at peak (phase = 0.5)
    tri.step(0.5)
    assert abs(tri.outputs["out"].read() - amplitude) < 1e-6


# =============================================================================
# SawtoothWave Tests
# =============================================================================


def test_sawtooth_starts_negative() -> None:
    """Sawtooth wave output is -amplitude at phase 0."""
    frequency = 1.0
    amplitude = 1.0
    saw = SawtoothWave("SAW1", frequency=frequency, amplitude=amplitude)

    # Initial step with dt=0 to measure starting value
    saw.step(0.0)
    assert abs(saw.outputs["out"].read() - (-amplitude)) < 1e-6


def test_sawtooth_ramps_up() -> None:
    """Sawtooth wave output increases with phase."""
    frequency = 1.0
    amplitude = 1.0
    saw = SawtoothWave("SAW1", frequency=frequency, amplitude=amplitude)

    # At 1/4 cycle (t=0.25 at 1 Hz)
    saw.step(0.25)
    output_at_quarter = saw.outputs["out"].read()
    # At phase 0.25, output should be -1 + 2*0.25 = -0.5
    assert abs(output_at_quarter - (-0.5)) < 1e-6

    # At 1/2 cycle (t=0.5 at 1 Hz)
    saw2 = SawtoothWave("SAW2", frequency=frequency, amplitude=amplitude)
    saw2.step(0.5)
    output_at_half = saw2.outputs["out"].read()
    # At phase 0.5, output should be -1 + 2*0.5 = 0.0
    assert abs(output_at_half - 0.0) < 1e-6

    # At 3/4 cycle (t=0.75 at 1 Hz)
    saw3 = SawtoothWave("SAW3", frequency=frequency, amplitude=amplitude)
    saw3.step(0.75)
    output_at_three_quarter = saw3.outputs["out"].read()
    # At phase 0.75, output should be -1 + 2*0.75 = 0.5
    assert abs(output_at_three_quarter - 0.5) < 1e-6


def test_sawtooth_amplitude() -> None:
    """Sawtooth wave respects amplitude parameter."""
    frequency = 1.0
    amplitude = 3.0
    saw = SawtoothWave("SAW1", frequency=frequency, amplitude=amplitude)

    # At phase 0.5 (midpoint), output should be 0
    saw.step(0.5)
    assert abs(saw.outputs["out"].read() - 0.0) < 1e-6

    # At phase 1.0 (end, wraps to 0), output should be -amplitude
    saw2 = SawtoothWave("SAW2", frequency=frequency, amplitude=amplitude)
    saw2.step(1.0)
    assert abs(saw2.outputs["out"].read() - (-amplitude)) < 1e-6


# =============================================================================
# SquareWave Tests
# =============================================================================


def test_square_wave_high() -> None:
    """Square wave output is +amplitude before duty_cycle."""
    frequency = 1.0
    amplitude = 1.0
    duty_cycle = 0.5
    sq = SquareWave("SQ1", frequency=frequency, amplitude=amplitude, duty_cycle=duty_cycle)

    # At t=0.25 (phase 0.25), which is < duty_cycle (0.5), should be high
    sq.step(0.25)
    assert abs(sq.outputs["out"].read() - amplitude) < 1e-6


def test_square_wave_low() -> None:
    """Square wave output is -amplitude after duty_cycle."""
    frequency = 1.0
    amplitude = 1.0
    duty_cycle = 0.5
    sq = SquareWave("SQ1", frequency=frequency, amplitude=amplitude, duty_cycle=duty_cycle)

    # At t=0.75 (phase 0.75), which is >= duty_cycle (0.5), should be low
    sq.step(0.75)
    assert abs(sq.outputs["out"].read() - (-amplitude)) < 1e-6


def test_square_wave_custom_duty_cycle() -> None:
    """Square wave respects custom duty cycle."""
    frequency = 1.0
    amplitude = 1.0
    duty_cycle = 0.3  # 30% high, 70% low

    sq = SquareWave("SQ1", frequency=frequency, amplitude=amplitude, duty_cycle=duty_cycle)

    # At t=0.2 (phase 0.2), which is < 0.3, should be high
    sq.step(0.2)
    assert abs(sq.outputs["out"].read() - amplitude) < 1e-6

    # At t=0.4 (phase 0.4), which is >= 0.3, should be low
    sq2 = SquareWave("SQ2", frequency=frequency, amplitude=amplitude, duty_cycle=duty_cycle)
    sq2.step(0.4)
    assert abs(sq2.outputs["out"].read() - (-amplitude)) < 1e-6


def test_square_wave_amplitude() -> None:
    """Square wave respects amplitude parameter."""
    frequency = 1.0
    amplitude = 2.5
    sq = SquareWave("SQ1", frequency=frequency, amplitude=amplitude)

    # At start (phase 0), should be high
    sq.step(0.0)
    assert abs(sq.outputs["out"].read() - amplitude) < 1e-6


# =============================================================================
# PiecewiseLinear Tests
# =============================================================================


def test_piecewise_identity() -> None:
    """Default breakpoints form identity function."""
    pw = PiecewiseLinear("PW1")

    # Default breakpoints are (-1, -1) and (1, 1), forming y = x
    test_values = [-1.0, -0.5, 0.0, 0.5, 1.0]
    for x_val in test_values:
        pw.inputs["in"].write(x_val)
        pw.step(0.1)
        assert abs(pw.outputs["out"].read() - x_val) < 1e-6


def test_piecewise_interpolation() -> None:
    """Piecewise linear interpolates between breakpoints."""
    # Breakpoints: (0, 0), (1, 2)
    # This gives y = 2x for 0 <= x <= 1
    pw = PiecewiseLinear("PW1", breakpoints=[(0.0, 0.0), (1.0, 2.0)])

    # At x=0.5, should be y=1.0 (interpolating between (0,0) and (1,2))
    pw.inputs["in"].write(0.5)
    pw.step(0.1)
    assert abs(pw.outputs["out"].read() - 1.0) < 1e-6

    # At x=0.25, should be y=0.5
    pw2 = PiecewiseLinear("PW2", breakpoints=[(0.0, 0.0), (1.0, 2.0)])
    pw2.inputs["in"].write(0.25)
    pw2.step(0.1)
    assert abs(pw2.outputs["out"].read() - 0.5) < 1e-6


def test_piecewise_multiple_segments() -> None:
    """Piecewise linear works with multiple segments."""
    # Breakpoints: (-1, 0), (0, 1), (1, 0) forms a triangle
    pw = PiecewiseLinear("PW1", breakpoints=[(-1.0, 0.0), (0.0, 1.0), (1.0, 0.0)])

    # At x=-0.5, interpolate between (-1, 0) and (0, 1)
    # t = (-0.5 - (-1)) / (0 - (-1)) = 0.5
    # y = 0 + 0.5 * (1 - 0) = 0.5
    pw.inputs["in"].write(-0.5)
    pw.step(0.1)
    assert abs(pw.outputs["out"].read() - 0.5) < 1e-6

    # At x=0.5, interpolate between (0, 1) and (1, 0)
    # t = (0.5 - 0) / (1 - 0) = 0.5
    # y = 1 + 0.5 * (0 - 1) = 0.5
    pw2 = PiecewiseLinear("PW2", breakpoints=[(-1.0, 0.0), (0.0, 1.0), (1.0, 0.0)])
    pw2.inputs["in"].write(0.5)
    pw2.step(0.1)
    assert abs(pw2.outputs["out"].read() - 0.5) < 1e-6


def test_piecewise_clamp() -> None:
    """Piecewise linear clamps output to range of input breakpoints."""
    # Breakpoints: (0, 0), (1, 1)
    pw = PiecewiseLinear("PW1", breakpoints=[(0.0, 0.0), (1.0, 1.0)])

    # Below minimum input (x < 0), clamp to first breakpoint output (y = 0)
    pw.inputs["in"].write(-1.0)
    pw.step(0.1)
    assert abs(pw.outputs["out"].read() - 0.0) < 1e-6

    # Above maximum input (x > 1), clamp to last breakpoint output (y = 1)
    pw2 = PiecewiseLinear("PW2", breakpoints=[(0.0, 0.0), (1.0, 1.0)])
    pw2.inputs["in"].write(2.0)
    pw2.step(0.1)
    assert abs(pw2.outputs["out"].read() - 1.0) < 1e-6


def test_piecewise_reset() -> None:
    """Piecewise linear reset clears output to 0."""
    pw = PiecewiseLinear("PW1", breakpoints=[(0.0, 0.0), (1.0, 2.0)])

    # Set an input and compute output
    pw.inputs["in"].write(0.5)
    pw.step(0.1)
    assert abs(pw.outputs["out"].read() - 1.0) < 1e-6

    # Reset should clear output to 0
    pw.reset()
    assert abs(pw.outputs["out"].read() - 0.0) < 1e-6
