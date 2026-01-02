from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from engine.machine import Machine
from engine.components.sources import VoltageSource
from tui.widgets.scope import Scope


class AnalogApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #top-row {
        layout: horizontal;
        height: 1fr;
        width: 100%;
    }

    #rack-pane {
        width: 30%;
        height: 100%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $boost;
        border-title-style: bold;
    }

    #scope-pane {
        width: 70%;
        height: 100%;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $boost;
        border-title-style: bold;
    }

    #controls-pane {
        width: 100%;
        height: 10;
        border: solid $accent;
        border-title-color: $text;
        border-title-background: $boost;
        border-title-style: bold;
    }

    #scope-widget {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        rack = Container(id="rack-pane")
        rack.border_title = "Rack"

        # Create scope widget to mount later
        self.scope = Scope(
            id="scope-widget",
            max_samples=1200,
            samples_per_pixel=20,
        )

        with Horizontal(id="top-row"):
            yield rack
            scope_pane = Container(self.scope, id="scope-pane")
            scope_pane.border_title = "Scope"
            yield scope_pane
        controls = Container(id="controls-pane")
        controls.border_title = "Controls"
        yield controls

    def on_mount(self) -> None:
        """Initialize simulation engine and set up update loops."""
        # Create machine with 1 ms timestep (1000 Hz)
        self.machine = Machine(dt=0.001)

        # Create 1 Hz sine wave voltage source
        voltage_source = VoltageSource(name="sine_1hz", frequency=1.0, amplitude=1.0)
        self.machine.add(voltage_source)
        self.voltage_source = voltage_source

        # Attach scope to voltage source output
        self.scope.set_source(voltage_source.outputs["out"])

        # Run simulation step at 1000 Hz (every 0.001 seconds)
        self.set_interval(0.001, self.simulation_step)

        # Update scope display at 30 FPS (every ~33ms)
        self.set_interval(1/30, self.update_scope)

    def simulation_step(self) -> None:
        """Execute one simulation step and collect output sample."""
        self.machine.step()

        self.scope.capture_sample()

    def update_scope(self) -> None:
        """Update scope display with current sample buffer."""
        if self.scope:
            self.scope.flush()


if __name__ == "__main__":
    AnalogApp().run()
