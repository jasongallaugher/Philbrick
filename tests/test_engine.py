import math
import pytest
from engine.signal import Signal, PatchPoint
from engine.components.sources import VoltageSource
from engine.machine import Machine


def test_signal_read_write() -> None:
    """Signal can be read and written."""
    signal = Signal(5.0)
    assert signal.read() == 5.0
    signal.write(10.0)
    assert signal.read() == 10.0


def test_patchpoint_read_write() -> None:
    """PatchPoint delegates read/write to Signal."""
    patch = PatchPoint("test")
    assert patch.read() == 0.0
    patch.write(7.5)
    assert patch.read() == 7.5


def test_voltage_source_sine() -> None:
    """VoltageSource outputs sine wave values."""
    v = VoltageSource("V1", 1.0, amplitude=1.0)

    # At t=0, sin(0) = 0
    v.step(0.0)
    assert abs(v.outputs["out"].read() - 0.0) < 1e-6

    # At t=0.25 (quarter period of 1Hz), sin(π/2) = 1
    v.step(0.25)
    assert abs(v.outputs["out"].read() - 1.0) < 1e-6

    # At t=0.5 (half period), sin(π) = 0
    v.step(0.25)
    assert abs(v.outputs["out"].read() - 0.0) < 1e-6

    # At t=0.75 (three-quarter period), sin(3π/2) = -1
    v.step(0.25)
    assert abs(v.outputs["out"].read() - (-1.0)) < 1e-6


def test_voltage_source_amplitude() -> None:
    """VoltageSource respects amplitude parameter."""
    v = VoltageSource("V2", 1.0, amplitude=2.0)
    v.step(0.25)
    assert abs(v.outputs["out"].read() - 2.0) < 1e-6


def test_machine_step() -> None:
    """Machine correctly advances time on each step."""
    machine = Machine(dt=0.001)
    assert machine.time == 0.0

    machine.step()
    assert abs(machine.time - 0.001) < 1e-9

    machine.step()
    assert abs(machine.time - 0.002) < 1e-9

    machine.step()
    assert abs(machine.time - 0.003) < 1e-9


def test_machine_reset() -> None:
    """Machine resets time to 0."""
    machine = Machine(dt=0.001)
    machine.step()
    machine.step()
    assert machine.time > 0.0

    machine.reset()
    assert machine.time == 0.0


def test_machine_reset_resets_components() -> None:
    """Machine reset calls reset on components."""
    machine = Machine(dt=0.25)
    v = VoltageSource("V1", 1.0, amplitude=1.0)
    machine.add(v)

    machine.step()
    assert abs(v.outputs["out"].read()) > 0.0

    machine.reset()
    assert machine.time == 0.0
    assert v.time == 0.0
    assert abs(v.outputs["out"].read() - 0.0) < 1e-6


def test_machine_with_voltage_source() -> None:
    """Machine correctly steps VoltageSource components."""
    machine = Machine(dt=0.25)
    v = VoltageSource("V1", 1.0, amplitude=1.0)
    machine.add(v)

    # At t=0, sin(0) = 0
    assert abs(v.outputs["out"].read() - 0.0) < 1e-6

    # Step 1: t advances to 0.25, sin(π/2) = 1
    machine.step()
    assert abs(machine.time - 0.25) < 1e-9
    assert abs(v.outputs["out"].read() - 1.0) < 1e-6

    # Step 2: t advances to 0.5, sin(π) = 0
    machine.step()
    assert abs(machine.time - 0.5) < 1e-9
    assert abs(v.outputs["out"].read() - 0.0) < 1e-6

    # Step 3: t advances to 0.75, sin(3π/2) = -1
    machine.step()
    assert abs(machine.time - 0.75) < 1e-9
    assert abs(v.outputs["out"].read() - (-1.0)) < 1e-6
