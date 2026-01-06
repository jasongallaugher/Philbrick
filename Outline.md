# Philbrick - Analog Computer Emulator

*Named after George Philbrick, pioneer of the operational amplifier.*

An LLM-driven analog computer simulator designed to explore the application of analog computing to LLM concepts like Transformers. Inspired by classic machines like the EAI 380 and Heathkit H1.

## Vision

```
┌─────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│    LLM      │ ───▶ │  Philbrick Simulator │ ───▶ │  Real Hardware  │
│  (designer) │ ◀─── │   (abstractions)     │      │   (eventual)    │
└─────────────┘      └─────────────────────┘      └─────────────────┘
```

## Goals

1. **LLM-native** - Abstractions and interfaces natural for LLMs to generate/manipulate
2. **Transformer exploration** - Build attention, softmax, and other primitives in analog
3. **Hardware path** - Maintain fidelity to real analog concepts for eventual physical implementation
4. **Educational** - Learn analog computing AND agentic development through building

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         TUI Layer (Textual)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ Patch    │ │ Component│ │ Scope    │ │ Control Panel      │  │
│  │ Panel    │ │ Rack     │ │ Display  │ │ (run/stop/reset)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Simulation Engine                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Machine  │ │ PatchBay │ │Component │ │ Signal   │            │
│  │ (clock)  │ │ (wiring) │ │ Registry │ │ Bus      │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Component Library                          │
│  Sources │ Math Ops │ Integrators │ Nonlinear │ I/O             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: TUI Scaffold + Minimal Engine

**Goal:** A running TUI with one component, one output, real-time updates.

### Step 0.1: Empty Textual App

Create the bare minimum Textual application that runs.

```python
# Just this - nothing more
from textual.app import App

class AnalogApp(App):
    pass

if __name__ == "__main__":
    AnalogApp().run()
```

**Checkpoint:** Run it. See an empty terminal app. Quit with Ctrl+C. Understand the app lifecycle.

---

### Step 0.2: Basic Layout Skeleton

Add the three main panes as placeholders.

```
┌─────────────────────────────────────────────────────────┐
│ ┌─ Rack ──────────┐ ┌─ Scope ─────────────────────────┐ │
│ │                 │ │                                 │ │
│ │  (empty)        │ │  (empty)                        │ │
│ │                 │ │                                 │ │
│ └─────────────────┘ └─────────────────────────────────┘ │
│ ┌─ Controls ──────────────────────────────────────────┐ │
│ │  (empty)                                            │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Checkpoint:** See the layout. Resize terminal, watch panes reflow. Understand Textual's CSS-like layout model.

---

### Step 0.3: Signal and Component Core

Implement the minimal engine classes (no TUI integration yet).

- `Signal` - a float value
- `PatchPoint` - named input/output with a Signal
- `Component` - base class with inputs, outputs, step()
- `VoltageSource` - outputs a sine wave

**Checkpoint:** Run in a Python REPL. Create a VoltageSource, call step() a few times, print the output value. Watch it climb the sine wave.

---

### Step 0.4: Machine and Time Loop

Implement the simulation orchestrator.

- `Machine` - holds components, manages time, runs step loop
- Fixed timestep (dt = 1ms = 1000 Hz)

```python
machine = Machine()
src = machine.add(VoltageSource("V1", frequency=1.0))
for _ in range(100):
    machine.step()
    print(f"t={machine.time:.3f}  V={src.outputs['out'].read():.3f}")
```

**Checkpoint:** See values printed. Verify the sine wave completes one cycle at t=1.0s. Understand the step loop.

---

### Step 0.5: ASCII Scope Widget (Static)

Build a scope widget that displays a buffer of samples as ASCII art.

- Fixed-size character grid
- Takes a list of floats, renders waveform
- No live updates yet - just static data

```
+10V ┤        ╭───╮
     │     ╭──╯   ╰──╮
  0V ┤─────╯         ╰─────
     │
-10V ┤
     └─────────────────────
```

**Checkpoint:** Pass in `[sin(x) for x in range(100)]`, see a sine wave rendered. Tweak the rendering until it looks right.

---

### Step 0.6: Wire Scope to Engine

Connect the simulation to the TUI.

- Machine runs in background (asyncio)
- Scope widget subscribes to a signal
- Display updates in real-time

**Checkpoint:** Launch app. See the sine wave drawing itself across the scope, live. This is the first "it's alive" moment.

---

### Step 0.7: Transport Controls

Add Run/Pause/Reset buttons.

- Run: start the simulation loop
- Pause: stop stepping, freeze display
- Reset: t=0, reset all component state

**Checkpoint:** Start, watch it run, pause, resume, reset. Verify reset actually resets (integrators would show this clearly once we have them).

---

### Phase 0 Complete

At this point you have:
- A working TUI with live visualization
- A clean engine architecture
- One component (VoltageSource)
- Understanding of how all the pieces connect

**Pause here.** Make sure everything is solid before Phase 1.

---

## Phase 1: Core Components + Patching

**Goal:** Enough primitives to wire up a differential equation solver.

### Step 1.1: PatchBay Implementation

Create the wiring system.

- `PatchBay` holds connections (output → inputs)
- `connect(source, dest)` creates a patch
- `propagate()` copies values through all patches

**Checkpoint:** In REPL, create two components, patch them, call propagate(), verify value flows. This is just plumbing - make sure it's solid.

---

### Step 1.2: Integrator Component

The heart of analog computation.

```python
class Integrator(Component):
    def __init__(self, name, initial=0.0, gain=1.0):
        self.state = initial  # This is the "memory"
        self.gain = gain
    
    def step(self, dt):
        self.state += self.inputs["in"].read() * self.gain * dt
        self.outputs["out"].write(self.state)
```

**Checkpoint:** Feed a constant 1.0 into an integrator. Watch output climb linearly (1.0, 2.0, 3.0... per second). This is ∫1 dt = t. If you understand why, you understand analog computing.

---

### Step 1.3: Summer and Coefficient

Simple arithmetic blocks.

- `Summer` - weighted sum of N inputs
- `Coefficient` - multiply by constant (the "pot")

**Checkpoint:** Sum two voltage sources. Multiply a signal by 0.5. Verify math is mathing.

---

### Step 1.4: Inverter

Trivial but essential - sign flip.

**Checkpoint:** Feed in +5, get -5. Done.

---

### Step 1.5: Patch Panel UI

Add patching to the TUI.

- Rack shows all components with their jacks
- Keyboard navigation: select component, select jack
- Key to create patch (maybe 'p' or Enter)
- Patches list shows current connections

```
Patches:
  V1.out → INT1.in
  INT1.out → INT2.in
```

**Checkpoint:** Create patches using keyboard only. See them listed. Verify signals flow.

---

### Step 1.6: Harmonic Oscillator

Wire up the classic first program.

```
  x'' = -ω²x
  
  ┌─────────┐    ┌─────────┐    ┌─────────┐
  │  INT1   │    │  INT2   │    │  COEF   │
  │  (x'')  │───▶│  (x')   │───▶│  -ω²    │──┐
  └─────────┘    └─────────┘    └─────────┘  │
       ▲                                      │
       └──────────────────────────────────────┘
```

- INT2 initial condition = 1.0 (starting position)
- COEF value = -1.0 (ω = 1)
- Output: cosine wave

**Checkpoint:** See the oscillator oscillate. This is the "hello world" of analog computing. If it works, you've built something real.

---

### Step 1.7: Multi-Channel Scope

Upgrade scope to show multiple signals.

- 2 channels minimum
- Different colors/styles (solid vs dashed in ASCII)
- Legend showing which signal is which

**Checkpoint:** Display both position (x) and velocity (x') from the oscillator. They should be 90° out of phase (sine and cosine).

---

### Phase 1 Complete

You now have:
- Working patching system
- Core analog compute primitives
- A real differential equation solver
- Multi-channel visualization

**Pause.** This is a natural stopping point. You've built an analog computer.

---

### Components Summary (Phase 1)

| Component    | Inputs | Outputs | Notes                        |
|--------------|--------|---------|------------------------------|
| VoltageSource| 0      | 1       | Constant, sine, step, ramp   |
| Summer       | N      | 1       | Weighted sum, configurable   |
| Integrator   | 1      | 1       | ∫in dt, with IC and gain     |
| Inverter     | 1      | 1       | Sign flip                    |
| Coefficient  | 1      | 1       | Multiply by constant (pot)   |

---

### Classic First Program: Harmonic Oscillator

```
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │    ┌─────────┐      ┌─────────┐      ┌─────────┐            │
  │    │  INT1   │      │  INT2   │      │  COEF   │            │
  │    │         │      │         │      │  -ω²    │            │
  │ ──▶│●in  out○│─────▶│●in  out○│─────▶│●in  out○│───┐        │
  │ │  │  (v→x') │      │  (x'→x) │      │         │   │        │
  │ │  └─────────┘      └─────────┘      └─────────┘   │        │
  │ │                                                   │        │
  │ └───────────────────────────────────────────────────┘        │
  │                    feedback loop                             │
  └─────────────────────────────────────────────────────────────┘
  
  Solving: x'' = -ω²x  (simple harmonic motion)
  INT2 initial condition = 1.0 (starting position)
  Output: x(t) = cos(ωt)
```

---

## Phase 2: Polish + Persistence (Future)

*Detailed steps to be written when Phase 1 is complete.*

### Likely Features

- Save/Load circuits (YAML)
- Component parameter editing in-app
- Improved scope (trigger modes, time base control)
- Preset circuits (oscillator, damped oscillator, etc.)

### TUI Layout (Phase 2 Target)

```
┌─ Analog Computer ──────────────────────────────────────────────────────┐
│                                                                        │
│ ┌─ Rack ──────────┐ ┌─ Scope ──────────────────┐ ┌─ Patches ────────┐ │
│ │                 │ │ CH1 ─── CH2 ---          │ │                  │ │
│ │ [SIN] V1        │ │                          │ │ V1.out → INT1.in │ │
│ │   ○ out         │ │ +10V┤    ╭─╮             │ │ INT1.out→INT2.in │ │
│ │                 │ │     │╭──╯  ╰──╮          │ │ INT2.out→COEF.in │ │
│ │ [∫] INT1        │ │   0V┤╯        ╰╮  ╭╮     │ │ COEF.out→INT1.in │ │
│ │   ● in  ○ out   │ │     │          ╰──╯╰─    │ │                  │ │
│ │   IC: 0.0       │ │ -10V┤                    │ │ [+ Add Patch]    │ │
│ │                 │ │     └────────────────    │ │ [× Clear All]    │ │
│ │ [∫] INT2        │ │                          │ │                  │ │
│ │   ● in  ○ out   │ │ T: 100ms/div  Trig: Auto │ │                  │ │
│ │   IC: 1.0       │ └──────────────────────────┘ └──────────────────┘ │
│ │                 │                                                   │
│ │ [×] COEF        │                                                   │
│ │   ● in  ○ out   │                                                   │
│ │   K: -1.0       │                                                   │
│ │                 │                                                   │
│ └─────────────────┘                                                   │
│                                                                        │
│ ┌─ Controls ───────────────────────────────────────────────────────┐  │
│ │ [▶ Run] [⏸ Pause] [↺ Reset]  │  Rate: 1000Hz  │  t = 1.234s      │  │
│ └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 3: Nonlinear + Advanced (Future)

*To be designed after Phase 2.*

### Candidate Components

| Component     | Function                          | Use Case                    |
|---------------|-----------------------------------|-----------------------------|
| Comparator    | Threshold → ±1                    | Control logic, limiting     |
| Multiplier    | x × y                             | Nonlinear systems, Lorenz   |
| Abs           | |x|                               | Rectification               |
| Noise         | White/pink noise source           | Stochastic systems          |

### Classic Programs to Explore

- **Lorenz Attractor** - chaos, requires 3 integrators + multipliers
- **Van der Pol Oscillator** - self-sustaining oscillator
- **Bouncing Ball** - requires comparator
- **Damped Oscillator** - add friction term to Phase 1 oscillator

---

## Technical Notes

### Simulation Approach

- **Fixed timestep** - simpler, predictable, good for real-time display
- **Euler integration** initially, upgrade to RK4 if drift is problematic
- **Topological sort** for component execution order (handle feedback correctly)
- **Saturation modeling** - optional ±10V or ±100V rails

### Stack

| Layer          | Technology        | Notes                              |
|----------------|-------------------|------------------------------------|
| TUI Framework  | Textual           | Modern, async, great widgets       |
| Plotting       | Custom ASCII      | Rich/Textual compatible            |
| Simulation     | Pure Python       | numpy optional for perf            |
| Integration    | scipy.solve_ivp   | On standby for RK45 if needed      |
| Persistence    | YAML              | Human-readable circuit files       |

### File Structure (Proposed)

```
philbrick/
├── __init__.py
├── engine/
│   ├── __init__.py
│   ├── signal.py        # Signal, PatchPoint
│   ├── component.py     # Component base, registry
│   ├── machine.py       # Simulation orchestration
│   └── components/
│       ├── __init__.py
│       ├── sources.py   # VoltageSource, Noise, FunctionGen
│       ├── math.py      # Summer, Coefficient, Inverter
│       ├── integrator.py
│       └── nonlinear.py # Multiplier, Comparator, Abs
├── tui/
│   ├── __init__.py
│   ├── app.py           # Main Textual app
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── rack.py      # Component rack display
│   │   ├── scope.py     # ASCII oscilloscope
│   │   ├── patches.py   # Patch list
│   │   └── controls.py  # Transport controls
│   └── styles.py        # CSS/styling
├── presets/
│   ├── harmonic.yaml
│   ├── lorenz.yaml
│   └── vanderpol.yaml
└── main.py
```

---

## Design Decisions

1. **Real-time only** (for now)
   - Matches physical hardware mental model
   - Simpler state management
   - Revisit speedup if we find ourselves waiting on slow systems

2. **Keyboard-only patching**
   - Vim-style navigation feels right
   - Keeps it terminal-native

3. **Fixed component set**
   - Start constrained, understand each primitive deeply
   - Clean internal architecture allows extension later
   - Plugin system is a Phase 4+ concern

4. **Explicit scope channels**
   - 2-4 channels, like a real scope
   - You choose what to watch, intentionally
   - Possible future: separate "DVM" widget for spot-checking any signal

5. **LLM integration: TBD**
   - The *application* is exploring analog computing + LLM intersection
   - Natural language → circuit is one possibility, but not the only one
   - Keep architecture clean; don't over-design for this yet

---

## Development Philosophy

**Patient. Deliberate. Meditative.**

This is a learning exercise, not a race. Each step should:

1. **Do one thing** - Small, focused changes
2. **Be runnable** - See it work (or break) immediately
3. **Be understandable** - Pause to internalize what happened and why
4. **Build on solid ground** - Don't move forward until current step is clear

The goal is *comprehension*, not completion. Speed is the enemy here.

---

## References

- Korn & Korn, *Electronic Analog Computers* (1956)
- Ulmann, *Analog Computing* (2013)
- Anabrid pyanalog: https://github.com/anabrid/pyanalog
- bdsim: https://petercorke.github.io/bdsim/
- The Analog Thing: https://the-analog-thing.org/

---

## Current Status

| Phase | Status | Summary |
|-------|--------|---------|
| 0 | ✓ Complete | TUI scaffold, transport controls, basic engine |
| 1 | ✓ Complete | PatchBay, Integrator, Summer, Coefficient, Inverter, multi-channel Scope |
| 2 | ✓ Complete | YAML circuits, CLI, registry, subcircuits, presets |
| 3 | ✓ Complete | Function generators, attention primitives |
| 4 | ✓ Complete | Hierarchical composition, Softmax & AttentionHead subcircuits |
| 5 | ✓ Complete | MCP server with 10 tools, rich feedback (110 tests passing) |

**Components:** 17 primitives + 2 subcircuits (Softmax, AttentionHead)

---

## MCP Server (Phase 5 - Complete)

**10 Tools Available:**
| Tool | Purpose |
|------|---------|
| `philbrick_list_components` | List available component/subcircuit types |
| `philbrick_create_circuit` | Initialize new circuit |
| `philbrick_add_component` | Add component by type and name |
| `philbrick_connect` | Wire source.port to dest.port |
| `philbrick_run` | Run simulation for N steps |
| `philbrick_read_signal` | Read current signal value |
| `philbrick_get_circuit_info` | Introspect circuit state |
| `philbrick_get_signal_stats` | Get min/max/mean/final for a signal |
| `philbrick_get_time_series` | Get signal history as array |
| `philbrick_check_settled` | Check if signal has stabilized |

**Run:** `uv run python mcp_server.py`

---

## Known Issues / Technical Debt

### Architectural (Deferred)

| Issue | Severity | Notes |
|-------|----------|-------|
| TUI bypasses CircuitDef loader | High | main.py loads YAML manually, misses subcircuit support/validation. Should unify on CircuitDef. |
| Global mutable state | Medium | MCP server and registry use module-level globals. Hard to run multiple circuits or isolate tests. |
| Implicit simulation ordering | Medium | One-tick latency from propagate→step ordering. Acceptable for now - mirrors real analog delay. |

### Bugs (Deferred)

| Issue | Severity | Notes |
|-------|----------|-------|
| Circuit serialization drops params | Medium | Round-tripping can change behavior - only subset of component params serialized. |

---

## Future Phases

### Phase 6: Transformer in Analog
- Multi-key attention with full softmax
- Multi-head attention composition
- Simple sequence processing demo
- Real hardware mapping (component values, op-amp circuits)
