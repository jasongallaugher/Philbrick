import math
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Footer
from textual.binding import Binding
from textual.color import Color
from engine.machine import Machine
from engine.components.sources import VoltageSource
from tui.widgets.scope import Scope


class AnalogApp(App):
    """Analog computer emulator TUI application."""

    BINDINGS = [
        Binding("space", "toggle_run", "Run/Pause", show=True),
        Binding("r", "reset", "Reset", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    # Color cycle for animated borders (white/light palette)
    _color_phase: float = 0.0

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
        border: solid;
        border-title-color: $text;
        border-title-background: $boost;
        border-title-style: bold;
    }

    #scope-pane {
        width: 70%;
        height: 100%;
        border: solid;
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
        
        yield Footer()

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

        # Track running state (starts paused)
        self.running = False

        # Simulation step timer at 1000 Hz (always running, checks self.running flag)
        self.set_interval(0.001, self.simulation_step)

        # Update scope display at 30 FPS (every ~33ms) - always runs
        self.set_interval(1/30, self.update_scope)

        # Animate border colors at ~2 Hz (smooth color transition)
        self.set_interval(0.5, self.update_border_color)
        # Start the animation immediately
        self.update_border_color()

    def update_border_color(self) -> None:
        """Update border color phase and apply to borders."""
        # Update phase
        self._color_phase = (self._color_phase + 0.15) % (2 * math.pi)
        
        # Generate color from phase using sine waves for smooth transitions
        # Cycle through white/light colors with visible variation:
        # white -> light cyan -> light blue -> light purple -> light pink -> white
        # Base is high (200-255) to keep it light, with 50 point variation for visibility
        phase = self._color_phase
        r = int(200 + 55 * (0.5 + 0.5 * math.sin(phase)))
        g = int(200 + 55 * (0.5 + 0.5 * math.sin(phase + 2 * math.pi / 3)))
        b = int(200 + 55 * (0.5 + 0.5 * math.sin(phase + 4 * math.pi / 3)))
        
        # Clamp to valid RGB range
        r = max(180, min(255, r))
        g = max(180, min(255, g))
        b = max(180, min(255, b))
        
        # Create color and convert to hex string for Textual
        color = Color(r, g, b)
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
        
        # Update border colors for both panes
        try:
            rack_pane = self.query_one("#rack-pane", Container)
            rack_pane.styles.border = ("solid", color_hex)
        except Exception:
            # Widget not found yet, will retry on next interval
            pass
        
        try:
            scope_pane = self.query_one("#scope-pane", Container)
            scope_pane.styles.border = ("solid", color_hex)
        except Exception:
            # Widget not found yet, will retry on next interval
            pass

    def simulation_step(self) -> None:
        """Execute one simulation step and collect output sample."""
        if not self.running:
            return
        self.machine.step()
        self.scope.capture_sample()

    def update_scope(self) -> None:
        """Update scope display with current sample buffer."""
        if self.scope:
            self.scope.flush()

    def action_toggle_run(self) -> None:
        """Toggle simulation run/pause state."""
        self.running = not self.running

    def action_reset(self) -> None:
        """Reset simulation to initial state."""
        self.running = False
        self.machine.reset()
        # Clear scope buffer
        self.scope.set_samples([])

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


if __name__ == "__main__":
    AnalogApp().run()
