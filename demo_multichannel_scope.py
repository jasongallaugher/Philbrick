#!/usr/bin/env python3
"""Demonstration of multi-channel scope functionality."""

import math
from engine.components.sources import VoltageSource
from engine.machine import Machine
from tui.widgets.scope import Scope


def demo_multi_channel():
    """Demonstrate multi-channel scope with two sine waves."""
    print("=" * 80)
    print("Multi-Channel Scope Demo")
    print("=" * 80)
    print()

    # Create machine
    machine = Machine(dt=0.01)

    # Create two voltage sources with different frequencies
    source1 = VoltageSource("V1", frequency=1.0, amplitude=1.0)  # 1 Hz
    source2 = VoltageSource("V2", frequency=2.0, amplitude=0.8)  # 2 Hz

    machine.add(source1)
    machine.add(source2)

    # Create scope with two channels
    scope = Scope(v_min=-1.0, v_max=1.0, max_samples=200, samples_per_pixel=2)

    # Add channels
    scope.add_channel(source1.outputs["out"], label="CH1")
    scope.add_channel(source2.outputs["out"], label="CH2")

    # Capture samples
    for _ in range(300):
        machine.step()
        scope.capture_sample()

    # Flush and render
    scope.flush()
    output = scope.render()

    print(output)
    print()
    print("Legend: CH1 uses '●' (solid), CH2 uses '○' (hollow)")
    print()


def demo_backward_compatibility():
    """Demonstrate that legacy single-channel mode still works."""
    print("=" * 80)
    print("Legacy Single-Channel Mode Demo")
    print("=" * 80)
    print()

    # Create machine
    machine = Machine(dt=0.01)

    # Create voltage source
    source = VoltageSource("V1", frequency=1.0, amplitude=1.0)
    machine.add(source)

    # Create scope using legacy set_source() method
    scope = Scope(v_min=-1.0, v_max=1.0, max_samples=200, samples_per_pixel=2)
    scope.set_source(source.outputs["out"])

    # Capture samples
    for _ in range(300):
        machine.step()
        scope.capture_sample()

    # Flush and render
    scope.flush()
    output = scope.render()

    print(output)
    print()


def demo_three_channels():
    """Demonstrate three channels with different signals."""
    print("=" * 80)
    print("Three-Channel Scope Demo")
    print("=" * 80)
    print()

    # Create machine
    machine = Machine(dt=0.01)

    # Create three voltage sources
    source1 = VoltageSource("V1", frequency=1.0, amplitude=0.9)
    source2 = VoltageSource("V2", frequency=1.5, amplitude=0.7)
    source3 = VoltageSource("V3", frequency=2.5, amplitude=0.5)

    machine.add(source1)
    machine.add(source2)
    machine.add(source3)

    # Create scope with three channels
    scope = Scope(v_min=-1.0, v_max=1.0, max_samples=200, samples_per_pixel=2)

    scope.add_channel(source1.outputs["out"], label="1Hz")
    scope.add_channel(source2.outputs["out"], label="1.5Hz")
    scope.add_channel(source3.outputs["out"], label="2.5Hz")

    # Capture samples
    for _ in range(400):
        machine.step()
        scope.capture_sample()

    # Flush and render
    scope.flush()
    output = scope.render()

    print(output)
    print()
    print("Legend: Different frequencies shown with different symbols")
    print()


if __name__ == "__main__":
    demo_backward_compatibility()
    print("\n" * 2)
    demo_multi_channel()
    print("\n" * 2)
    demo_three_channels()
