import sys
from pathlib import Path
import yaml
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Static
from textual.binding import Binding
from engine.machine import Machine
from engine.patchbay import PatchBay
from engine.registry import create_component
from engine.utils import parse_port_ref
from tui.widgets.scope import Scope
from tui.widgets.patches import PatchList


def load_preset(preset_path: Path) -> dict:
    """Load a preset YAML file."""
    with open(preset_path) as f:
        return yaml.safe_load(f)


def list_presets() -> list[Path]:
    """List all available preset files."""
    presets_dir = Path(__file__).parent / "presets"
    return sorted(presets_dir.glob("*.yaml"))


class AnalogApp(App):
    """Analog computer emulator TUI application."""

    BINDINGS = [
        Binding("space", "toggle_run", "Run/Pause", show=True),
        Binding("r", "reset", "Reset", show=True),
        Binding("n", "next_preset", "Next Preset", show=True),
        Binding("p", "prev_preset", "Prev Preset", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

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
        width: 25%;
        height: 100%;
        border: solid;
        border-title-color: $text;
        border-title-background: $boost;
        border-title-style: bold;
        padding: 1;
        overflow-y: auto;
    }

    #scope-pane {
        width: 55%;
        height: 100%;
        border: solid;
        border-title-color: $text;
        border-title-background: $boost;
        border-title-style: bold;
    }

    #patches-pane {
        width: 20%;
        height: 100%;
        border: solid;
        border-title-color: $text;
        border-title-background: $boost;
        border-title-style: bold;
        padding: 1;
        overflow-y: auto;
    }

    #scope-widget {
        width: 100%;
        height: 100%;
    }

    .component-info {
        margin-bottom: 1;
    }
    """

    def __init__(self, preset_path: Path | None = None):
        super().__init__()
        self.presets = list_presets()
        self.preset_index = 0

        # Find initial preset
        if preset_path:
            for i, p in enumerate(self.presets):
                if p == preset_path or p.stem == preset_path.stem:
                    self.preset_index = i
                    break

    def compose(self) -> ComposeResult:
        # Create scope widget
        self.scope = Scope(
            id="scope-widget",
            max_samples=1200,
            samples_per_pixel=20,
        )

        # Initialize patchbay and machine
        self.patchbay = PatchBay()
        self.machine = Machine(dt=0.001)

        # Create rack content (will be updated when preset loads)
        self.rack_info = Static("Loading...", classes="component-info")

        # Create patch list widget
        self.patch_list = PatchList(self.patchbay, self.machine)

        with Horizontal(id="top-row"):
            rack = Container(self.rack_info, id="rack-pane")
            rack.border_title = "Rack"
            yield rack

            scope_pane = Container(self.scope, id="scope-pane")
            scope_pane.border_title = "Scope"
            yield scope_pane

            patches_pane = Container(self.patch_list, id="patches-pane")
            patches_pane.border_title = "Patches"
            yield patches_pane

        yield Footer()

    def on_mount(self) -> None:
        """Initialize simulation engine and set up update loops."""
        # Track running state (starts paused)
        self.running = False
        self.components = {}

        # Load initial preset
        self._load_current_preset()

        # Simulation step timer at 1000 Hz
        self.set_interval(0.001, self.simulation_step)

        # Update scope display at 30 FPS
        self.set_interval(1/30, self.update_scope)

    def _load_current_preset(self) -> None:
        """Load the currently selected preset."""
        if not self.presets:
            self.rack_info.update("[red]No presets found![/red]")
            return

        preset_path = self.presets[self.preset_index]
        preset = load_preset(preset_path)
        self._build_circuit(preset)

    def _build_circuit(self, preset: dict) -> None:
        """Build circuit from preset definition."""
        # Stop simulation
        self.running = False

        # Clear existing state
        self.patchbay.clear()
        self.machine = Machine(dt=0.001)
        self.components = {}

        # Update patch list reference
        self.patch_list.patchbay = self.patchbay
        self.patch_list.machine = self.machine

        # Build rack info display
        name = preset.get("name", "Unnamed")
        desc = preset.get("description", "").strip()
        # Truncate description for display
        desc_lines = desc.split("\n")[:4]
        desc_short = "\n".join(desc_lines)
        if len(desc.split("\n")) > 4:
            desc_short += "\n..."

        components_list = preset.get("components", [])
        comp_names = [c["name"] for c in components_list]

        rack_text = f"[b]{name}[/b]\n\n"
        rack_text += f"[dim]{desc_short}[/dim]\n\n"
        rack_text += f"[b]Components ({len(comp_names)}):[/b]\n"
        for c in components_list[:8]:  # Show first 8
            rack_text += f"  {c['name']}: {c['type']}\n"
        if len(components_list) > 8:
            rack_text += f"  ... +{len(components_list) - 8} more"

        self.rack_info.update(rack_text)

        # Create components
        for comp_def in components_list:
            comp = create_component(
                comp_def["type"],
                comp_def["name"],
                comp_def.get("params", {})
            )
            self.machine.add(comp)
            self.components[comp_def["name"]] = comp

        # Create patches
        for patch in preset.get("patches", []):
            src_name, src_port = parse_port_ref(patch[0])
            dst_name, dst_port = parse_port_ref(patch[1])

            src_comp = self.components[src_name]
            dst_comp = self.components[dst_name]

            self.patchbay.connect(
                src_comp.outputs[src_port],
                dst_comp.inputs[dst_port]
            )

        # Configure scope channels
        self.scope.clear_channels()
        scope_config = preset.get("scope", {})
        channels = scope_config.get("channels", [])

        for ch in channels[:4]:  # Max 4 channels
            src_name, src_port = parse_port_ref(ch["source"])
            comp = self.components[src_name]
            port = comp.outputs.get(src_port) or comp.inputs.get(src_port)
            if port:
                self.scope.add_channel(port, label=ch.get("label", ch["source"]))

        # Clear scope display
        for channel in self.scope.channels:
            channel.buffer.clear()
        self.scope.set_samples([])

        # Update patch list display
        self.patch_list.refresh()

    def simulation_step(self) -> None:
        """Execute one simulation step and collect output sample."""
        if not self.running:
            return
        # Propagate signals through patches first
        self.patchbay.propagate()
        # Then step all components
        self.machine.step()
        # Capture scope samples
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
        # Clear all channel buffers
        for channel in self.scope.channels:
            channel.buffer.clear()
        self.scope.set_samples([])

    def action_next_preset(self) -> None:
        """Load next preset."""
        if self.presets:
            self.preset_index = (self.preset_index + 1) % len(self.presets)
            self._load_current_preset()

    def action_prev_preset(self) -> None:
        """Load previous preset."""
        if self.presets:
            self.preset_index = (self.preset_index - 1) % len(self.presets)
            self._load_current_preset()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


if __name__ == "__main__":
    # Parse optional preset argument
    preset_path = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # Check if it's a path or just a preset name
        if arg.endswith(".yaml"):
            preset_path = Path(arg)
        else:
            preset_path = Path(__file__).parent / "presets" / f"{arg}.yaml"

    AnalogApp(preset_path).run()
