import math

from engine.component import Component
from engine.signal import PatchPoint


class TriangleWave(Component):
    """Generates a triangle wave oscillator."""

    def __init__(
        self, name: str, frequency: float, amplitude: float = 1.0
    ) -> None:
        super().__init__(name)
        self.frequency: float = frequency
        self.amplitude: float = amplitude
        self.time: float = 0.0
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Update internal time and generate triangle wave output."""
        self.time += dt
        # Sawtooth phase from 0 to 1
        phase = (self.frequency * self.time) % 1.0
        # Triangle: rises from -1 to 1 in first half, falls from 1 to -1 in second half
        if phase < 0.5:
            value = -1.0 + 4.0 * phase  # rises from -1 to 1
        else:
            value = 3.0 - 4.0 * phase  # falls from 1 to -1
        self.outputs["out"].write(self.amplitude * value)

    def reset(self) -> None:
        """Reset internal time and output to initial state."""
        self.time = 0.0
        self.outputs["out"].write(-self.amplitude)


class SawtoothWave(Component):
    """Generates a sawtooth wave oscillator."""

    def __init__(
        self, name: str, frequency: float, amplitude: float = 1.0
    ) -> None:
        super().__init__(name)
        self.frequency: float = frequency
        self.amplitude: float = amplitude
        self.time: float = 0.0
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Update internal time and generate sawtooth wave output."""
        self.time += dt
        # Sawtooth phase from 0 to 1
        phase = (self.frequency * self.time) % 1.0
        # Ramp from -1 to 1 linearly across the period
        value = -1.0 + 2.0 * phase
        self.outputs["out"].write(self.amplitude * value)

    def reset(self) -> None:
        """Reset internal time and output to initial state."""
        self.time = 0.0
        self.outputs["out"].write(-self.amplitude)


class SquareWave(Component):
    """Generates a square wave oscillator with configurable duty cycle."""

    def __init__(
        self,
        name: str,
        frequency: float,
        amplitude: float = 1.0,
        duty_cycle: float = 0.5,
    ) -> None:
        super().__init__(name)
        self.frequency: float = frequency
        self.amplitude: float = amplitude
        self.duty_cycle: float = duty_cycle
        self.time: float = 0.0
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Update internal time and generate square wave output."""
        self.time += dt
        # Phase from 0 to 1
        phase = (self.frequency * self.time) % 1.0
        # High if in first duty_cycle portion, low otherwise
        value = self.amplitude if phase < self.duty_cycle else -self.amplitude
        self.outputs["out"].write(value)

    def reset(self) -> None:
        """Reset internal time and output to initial state."""
        self.time = 0.0
        self.outputs["out"].write(self.amplitude)


class PiecewiseLinear(Component):
    """Piecewise linear function mapping input to output via breakpoints."""

    def __init__(self, name: str, breakpoints: list[tuple[float, float]] | None = None) -> None:
        super().__init__(name)
        # Default breakpoints form identity: (-1, -1), (1, 1)
        self.breakpoints: list[tuple[float, float]] = (
            breakpoints if breakpoints is not None else [(-1.0, -1.0), (1.0, 1.0)]
        )
        # Sort by input value
        self.breakpoints.sort(key=lambda bp: bp[0])
        self.inputs["in"] = PatchPoint("in")
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Interpolate input through piecewise linear function."""
        input_value = self.inputs["in"].read()
        output_value = self._interpolate(input_value)
        self.outputs["out"].write(output_value)

    def _interpolate(self, x: float) -> float:
        """Linear interpolation through breakpoints with clamping at edges."""
        # Clamp to first and last input values
        if x <= self.breakpoints[0][0]:
            return self.breakpoints[0][1]
        if x >= self.breakpoints[-1][0]:
            return self.breakpoints[-1][1]

        # Find the two breakpoints to interpolate between
        for i in range(len(self.breakpoints) - 1):
            x1, y1 = self.breakpoints[i]
            x2, y2 = self.breakpoints[i + 1]
            if x1 <= x <= x2:
                # Linear interpolation
                t = (x - x1) / (x2 - x1)
                return y1 + t * (y2 - y1)

        return self.breakpoints[-1][1]

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)
