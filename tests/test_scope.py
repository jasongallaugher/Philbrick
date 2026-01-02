"""Tests for ASCII Scope widget."""

import math
import pytest
from engine.components.sources import VoltageSource
from engine.machine import Machine
from tui.widgets.scope import Scope


def test_scope_renders() -> None:
    """Scope widget renders sine wave samples as ASCII art."""
    # Create sine wave samples
    num_samples = 80
    samples = [math.sin(2 * math.pi * i / num_samples) for i in range(num_samples)]

    # Create Scope widget
    scope = Scope(samples=samples, v_min=-1.0, v_max=1.0)

    # Render output
    output = scope.render()

    # Verify output is non-empty string
    assert isinstance(output, str)
    assert len(output) > 0
    assert '\n' in output  # Should have multiple lines

    # Verify it contains expected characters
    assert '│' in output or '─' in output or '+' in output


def test_scope_set_samples() -> None:
    """Scope.set_samples updates the waveform data."""
    scope = Scope()
    assert scope.samples == []

    samples = [0.0, 0.5, 1.0, 0.5, 0.0, -0.5, -1.0, -0.5]
    scope.set_samples(samples)

    assert scope.samples == samples
    output = scope.render()
    assert isinstance(output, str)
    assert len(output) > 0


def test_scope_empty_samples() -> None:
    """Scope handles empty samples gracefully."""
    scope = Scope(samples=[])
    output = scope.render()

    assert isinstance(output, str)
    assert "No data" in output


def test_scope_voltage_scaling() -> None:
    """Scope respects custom voltage scale."""
    samples = [0.0, 2.5, 5.0, 2.5]
    scope = Scope(samples=samples, v_min=0.0, v_max=5.0)

    output = scope.render()
    assert isinstance(output, str)
    assert len(output) > 0


def test_scope_captures_from_signal() -> None:
    """Scope captures samples from a signal source."""
    machine = Machine(dt=0.25)
    source = VoltageSource("V1", 1.0, amplitude=1.0)
    machine.add(source)

    scope = Scope(max_samples=5)
    scope.set_source(source.outputs["out"])

    for _ in range(7):
        machine.step()
        scope.capture_sample()

    scope.flush()

    assert len(scope.samples) == 5
    assert abs(scope.samples[-1] - source.outputs["out"].read()) < 1e-6
