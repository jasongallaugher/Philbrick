import pytest
from engine.signal import PatchPoint
from engine.patchbay import PatchBay


def test_connect_and_propagate() -> None:
    """Connect two PatchPoints, write to source, propagate, verify dest has value."""
    patchbay = PatchBay()
    source = PatchPoint("source")
    dest = PatchPoint("dest")

    source.write(5.0)
    patchbay.connect(source, dest)
    patchbay.propagate()

    assert dest.read() == 5.0


def test_fan_out() -> None:
    """One source connected to multiple destinations, propagate copies to all."""
    patchbay = PatchBay()
    source = PatchPoint("source")
    dest1 = PatchPoint("dest1")
    dest2 = PatchPoint("dest2")
    dest3 = PatchPoint("dest3")

    source.write(7.5)
    patchbay.connect(source, dest1)
    patchbay.connect(source, dest2)
    patchbay.connect(source, dest3)
    patchbay.propagate()

    assert dest1.read() == 7.5
    assert dest2.read() == 7.5
    assert dest3.read() == 7.5


def test_disconnect() -> None:
    """Connect, then disconnect, propagate should NOT copy value."""
    patchbay = PatchBay()
    source = PatchPoint("source")
    dest = PatchPoint("dest")

    patchbay.connect(source, dest)
    patchbay.disconnect(source, dest)

    source.write(10.0)
    patchbay.propagate()

    assert dest.read() == 0.0


def test_clear() -> None:
    """Connect multiple, clear, propagate should NOT copy values."""
    patchbay = PatchBay()
    source1 = PatchPoint("source1")
    source2 = PatchPoint("source2")
    dest1 = PatchPoint("dest1")
    dest2 = PatchPoint("dest2")

    patchbay.connect(source1, dest1)
    patchbay.connect(source2, dest2)
    patchbay.clear()

    source1.write(3.0)
    source2.write(6.0)
    patchbay.propagate()

    assert dest1.read() == 0.0
    assert dest2.read() == 0.0


def test_propagate_empty() -> None:
    """Propagate with no connections doesn't error."""
    patchbay = PatchBay()
    patchbay.propagate()  # Should not raise an exception
