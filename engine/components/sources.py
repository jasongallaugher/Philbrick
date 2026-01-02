import math
from engine.component import Component
from engine.signal import PatchPoint


class VoltageSource(Component):
    """Generates a sinusoidal voltage output."""

    def __init__(
        self, name: str, frequency: float, amplitude: float = 1.0
    ) -> None:
        super().__init__(name)
        self.frequency: float = frequency
        self.amplitude: float = amplitude
        self.time: float = 0.0
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Update internal time and set output to sin(2π × frequency × time)."""
        self.time += dt
        value = self.amplitude * math.sin(2 * math.pi * self.frequency * self.time)
        self.outputs["out"].write(value)

    def reset(self) -> None:
        """Reset internal time and output to initial state."""
        self.time = 0.0
        self.outputs["out"].write(0.0)
