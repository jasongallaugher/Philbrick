# Philbrick

An LLM-driven analog computer simulator for exploring Transformer implementations in analog hardware.

```
LLM  <-->  Analog Simulator  <-->  Real Hardware
```

## Vision

Philbrick bridges the gap between modern AI and classic analog computing. Named after George A. Philbrick, pioneer of operational amplifiers, this project explores how Transformer architecture concepts (attention, softmax, layer normalization) can be implemented using analog computing primitives.

The simulator is designed to be driven by LLMs through an MCP (Model Context Protocol) server, enabling AI-assisted circuit design and exploration.

## Features

### Analog Computing Primitives
- **Integrators** - Core of analog computation, solve differential equations
- **Summers** - Weighted addition of signals
- **Multipliers** - Four-quadrant analog multiplication
- **Coefficients** - Signal scaling (the classic "pot")
- **Comparators, Limiters** - Nonlinear operations
- **Exp, Divider** - For attention/softmax implementations
- **Function Generators** - Triangle, sawtooth, square waves

### Subcircuit Composition
- Define reusable circuit blocks as YAML
- Built-in: Softmax, AttentionHead
- Automatic port mapping and internal wiring

### MCP Server (13 tools)
```
philbrick_list_components    - List available component types
philbrick_create_circuit     - Initialize a new circuit
philbrick_add_component      - Add component to circuit
philbrick_connect            - Wire components together
philbrick_run                - Run simulation steps
philbrick_read_signal        - Read port value + sparkline
philbrick_get_circuit_info   - Get circuit topology
philbrick_get_circuit_diagram - ASCII circuit diagram
philbrick_get_signal_stats   - Min/max/mean + sparkline
philbrick_get_time_series    - Full signal history
philbrick_check_settled      - Detect signal convergence
philbrick_get_phase_portrait - ASCII x-vs-y plots
```

### TUI Oscilloscope
Real-time visualization with multi-channel scope, transport controls, and preset switching.

## Quick Start

```bash
# Install dependencies
uv sync

# Run TUI with preset selector
uv run main.py

# Or start with a specific preset
uv run main.py lorenz
uv run main.py van_der_pol

# Run tests
uv run pytest
```

### TUI Controls
- `Space` - Run/Pause simulation
- `R` - Reset to initial conditions
- `N` / `P` - Next/Previous preset
- `Q` - Quit

## Presets

| Preset | Description |
|--------|-------------|
| `harmonic_oscillator` | Classic x'' = -x, produces sine waves |
| `damped_oscillator` | Decaying oscillations |
| `second_order_system` | Configurable damping and frequency |
| `van_der_pol` | Nonlinear limit cycle oscillator |
| `lorenz` | Chaotic butterfly attractor |
| `amplitude_modulation` | AM signal generation |
| `voltage_ramp` | Simple integrator ramp |

## Architecture

```
engine/
  machine.py      - Simulation engine, timestep control
  patchbay.py     - Signal routing between components
  signal.py       - PatchPoint for component I/O
  component.py    - Base component class
  registry.py     - Component/subcircuit factory
  subcircuit.py   - Subcircuit composition system
  components/     - All analog primitives

tui/
  widgets/
    scope.py      - Multi-channel oscilloscope
    patches.py    - Patch list display

presets/          - YAML circuit definitions
mcp_server.py     - MCP server for LLM integration
```

## Example: Lorenz Attractor

The Lorenz system demonstrates deterministic chaos:

```
dx/dt = σ(y - x)
dy/dt = x(ρ - z) - y
dz/dt = xy - βz
```

With σ=10, ρ=28, β=8/3, the system traces the famous butterfly attractor - trajectories never repeat but stay bounded within a fractal structure.

Run `uv run main.py lorenz` and press Space to watch chaos emerge.

## MCP Integration

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "philbrick": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py"],
      "cwd": "/path/to/Philbrick"
    }
  }
}
```

Then ask Claude to build and simulate analog circuits.

## License

MIT
