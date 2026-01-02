from abc import ABC, abstractmethod
from engine.signal import PatchPoint


class Component(ABC):
    """Base class for analog computer components."""

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.inputs: dict[str, PatchPoint] = {}
        self.outputs: dict[str, PatchPoint] = {}

    @abstractmethod
    def step(self, dt: float) -> None:
        """Execute one simulation step."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset component state to initial conditions."""
        pass
