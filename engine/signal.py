class Signal:
    """Holds a float value for signal transmission."""

    def __init__(self, initial_value: float = 0.0) -> None:
        self._value: float = initial_value

    def read(self) -> float:
        """Read the current signal value."""
        return self._value

    def write(self, value: float) -> None:
        """Write a new signal value."""
        self._value = value


class PatchPoint:
    """Named input or output connection point with an associated Signal."""

    def __init__(self, name: str, signal: Signal | None = None) -> None:
        self.name: str = name
        self.signal: Signal = signal if signal is not None else Signal()

    def read(self) -> float:
        """Read value from the connected signal."""
        return self.signal.read()

    def write(self, value: float) -> None:
        """Write value to the connected signal."""
        self.signal.write(value)
