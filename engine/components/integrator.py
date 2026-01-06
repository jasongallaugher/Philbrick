from engine.component import Component
from engine.signal import PatchPoint


class Integrator(Component):
    """The heart of analog computation - integrates input over time."""

    def __init__(
        self, name: str, initial: float = 0.0, gain: float = 1.0
    ) -> None:
        super().__init__(name)
        self.initial: float = initial
        self.gain: float = gain
        self.state: float = initial
        self.inputs["in"] = PatchPoint("in")
        self.outputs["out"] = PatchPoint("out")
        self.outputs["out"].write(self.state)

    def step(self, dt: float) -> None:
        """Integrate input: state += input * gain * dt."""
        input_value = self.inputs["in"].read()
        self.state += input_value * self.gain * dt
        self.outputs["out"].write(self.state)

    def reset(self) -> None:
        """Reset state to initial value and clear output."""
        self.state = self.initial
        self.outputs["out"].write(self.state)
