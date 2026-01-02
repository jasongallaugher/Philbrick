from engine.component import Component


class Machine:
    """Orchestrates simulation execution for registered components."""

    def __init__(self, dt: float = 0.001) -> None:
        """
        Initialize the simulation machine.

        Args:
            dt: Fixed timestep in seconds (default 0.001 = 1ms = 1000Hz)
        """
        self.time: float = 0.0
        self.dt: float = dt
        self.components: list[Component] = []

    def add(self, component: Component) -> Component:
        """
        Register a component with the machine.

        Args:
            component: Component to register

        Returns:
            The registered component (for chaining)
        """
        self.components.append(component)
        return component

    def step(self) -> None:
        """Advance simulation by one timestep, calling step(dt) on all components."""
        self.time += self.dt
        for component in self.components:
            component.step(self.dt)

    def reset(self) -> None:
        """Reset simulation time and component state."""
        self.time = 0.0
        for component in self.components:
            component.reset()
