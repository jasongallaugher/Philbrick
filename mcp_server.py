"""MCP server for the Philbrick analog computer simulator.

Provides tools for creating and manipulating analog circuits, including:
- Listing available component types
- Creating circuits
- Adding components
- Connecting components
- Running simulations
- Reading signal values
- Querying circuit information
"""

from mcp.server.fastmcp import FastMCP
from engine.machine import Machine
from engine.patchbay import PatchBay
from engine.component import Component
from engine.registry import list_component_types, create_component, is_subcircuit
from engine.subcircuits.softmax import register_softmax
from engine.subcircuits.attention import register_attention_head
from engine.utils import parse_port_ref
import statistics

# Initialize MCP server
mcp = FastMCP("Philbrick")


def _make_sparkline(values: list[float], width: int = 20) -> str:
    """Generate ASCII sparkline from values.

    Args:
        values: List of numeric values to visualize
        width: Maximum width of the sparkline in characters (default: 20)

    Returns:
        str: ASCII sparkline using unicode block characters
    """
    if not values:
        return ""
    chars = "▁▂▃▄▅▆▇█"
    min_v, max_v = min(values), max(values)
    range_v = max_v - min_v if max_v != min_v else 1
    # Sample down to width if needed
    step = max(1, len(values) // width)
    samples = values[::step][:width]
    return "".join(chars[min(7, int((v - min_v) / range_v * 7.99))] for v in samples)

# Module-level state for the circuit
_machine: Machine | None = None
_patchbay: PatchBay | None = None
_components: dict[str, Component] = {}

# Module-level signal history tracking
_signal_history: dict[str, list[float]] = {}  # port -> list of values

# Maximum signal history size to prevent unbounded memory growth
_MAX_SIGNAL_HISTORY = 100000  # 100k samples


# Register subcircuits at module load
register_softmax()
register_attention_head()


@mcp.tool()
def philbrick_list_components() -> dict:
    """List all available component types.

    Returns information about all registered component and subcircuit types
    available for instantiation.

    Returns:
        dict: Contains 'components' key with a list of available type names
    """
    types = list_component_types()
    return {"components": types, "count": len(types)}


@mcp.tool()
def philbrick_create_circuit() -> dict:
    """Create a new circuit and initialize the simulation machine.

    Creates a fresh machine and patch bay for building a new circuit.
    This resets any previously created circuit.

    Returns:
        dict: Success message and initialization details
    """
    global _machine, _patchbay, _components, _signal_history

    _machine = Machine(dt=0.001)  # 1ms timestep
    _patchbay = PatchBay()
    _components = {}
    _signal_history = {}  # Clear signal history

    return {
        "status": "success",
        "message": "Circuit created successfully",
        "machine": {
            "time": _machine.time,
            "dt": _machine.dt,
            "components_count": 0,
        },
    }


@mcp.tool()
def philbrick_add_component(
    component_type: str, name: str, params: dict | None = None
) -> dict:
    """Add a component to the circuit.

    Creates a new component instance and adds it to the machine.
    For subcircuits, the machine and patchbay are automatically provided.

    Args:
        component_type: Type of component to create (e.g., "Integrator", "Softmax")
        name: Unique name for this component instance
        params: Optional dictionary of component-specific parameters

    Returns:
        dict: Success status and component details

    Raises:
        ValueError: If circuit hasn't been created or component creation fails
    """
    global _machine, _patchbay, _components

    if _machine is None or _patchbay is None:
        raise ValueError("Circuit not initialized. Call philbrick_create_circuit first.")

    if name in _components:
        raise ValueError(f"Component '{name}' already exists in circuit")

    try:
        # For subcircuits, provide machine and patchbay in params
        create_params = params or {}
        if is_subcircuit(component_type):
            create_params["machine"] = _machine
            create_params["patchbay"] = _patchbay

        component = create_component(component_type, name, create_params)
        _machine.add(component)
        _components[name] = component

        # Get port information
        input_ports = list(component.inputs.keys())
        output_ports = list(component.outputs.keys())

        return {
            "status": "success",
            "name": name,
            "type": component_type,
            "inputs": input_ports,
            "outputs": output_ports,
            "message": f"Component '{name}' of type '{component_type}' added successfully",
        }

    except Exception as e:
        raise ValueError(f"Failed to create component: {str(e)}")


@mcp.tool()
def philbrick_connect(source: str, dest: str) -> dict:
    """Connect a source port to a destination port.

    Creates a patch connection from a source component output to a destination
    component input. Port format is "COMPONENT.port" (e.g., "INT1.out").

    Args:
        source: Source port in format "component_name.port_name"
        dest: Destination port in format "component_name.port_name"

    Returns:
        dict: Success status and connection details

    Raises:
        ValueError: If circuit not initialized or ports not found
    """
    global _machine, _patchbay, _components

    if _patchbay is None:
        raise ValueError("Circuit not initialized. Call philbrick_create_circuit first.")

    try:
        # Parse source and destination ports
        src_comp_name, src_port_name = parse_port_ref(source)
        dst_comp_name, dst_port_name = parse_port_ref(dest)

        # Get components
        src_component = _components.get(src_comp_name)
        dst_component = _components.get(dst_comp_name)

        if src_component is None:
            raise ValueError(f"Component '{src_comp_name}' not found")
        if dst_component is None:
            raise ValueError(f"Component '{dst_comp_name}' not found")

        # Get ports
        src_port = src_component.outputs.get(src_port_name)
        if src_port is None:
            raise ValueError(
                f"Component '{src_comp_name}' has no output port '{src_port_name}'"
            )

        dst_port = dst_component.inputs.get(dst_port_name)
        if dst_port is None:
            raise ValueError(
                f"Component '{dst_comp_name}' has no input port '{dst_port_name}'"
            )

        # Create connection
        _patchbay.connect(src_port, dst_port)

        return {
            "status": "success",
            "source": source,
            "destination": dest,
            "message": f"Connected '{source}' to '{dest}'",
        }

    except ValueError as e:
        raise ValueError(f"Connection failed: {str(e)}")


@mcp.tool()
def philbrick_run(steps: int = 100) -> dict:
    """Run the simulation for a specified number of steps.

    Executes the simulation loop: propagates patches, steps all components,
    and advances time. Records signal history for all component outputs.

    Args:
        steps: Number of simulation steps to execute (default: 100)

    Returns:
        dict: Final simulation time and step count

    Raises:
        ValueError: If circuit not initialized
    """
    global _machine, _patchbay, _components, _signal_history

    if _machine is None or _patchbay is None:
        raise ValueError("Circuit not initialized. Call philbrick_create_circuit first.")

    if steps < 1:
        raise ValueError("Steps must be at least 1")

    try:
        for _ in range(steps):
            _patchbay.propagate()
            _machine.step()

            # Record signal history for all component outputs
            for comp_name, component in _components.items():
                for port_name, port in component.outputs.items():
                    port_key = f"{comp_name}.{port_name}"
                    if port_key not in _signal_history:
                        _signal_history[port_key] = []
                    _signal_history[port_key].append(port.read())
                    # Trim history if over limit to prevent unbounded memory growth
                    if len(_signal_history[port_key]) > _MAX_SIGNAL_HISTORY:
                        _signal_history[port_key] = _signal_history[port_key][-_MAX_SIGNAL_HISTORY:]

        return {
            "status": "success",
            "final_time": _machine.time,
            "steps_executed": steps,
            "message": f"Simulation completed: {steps} steps, final time {_machine.time}s",
        }

    except Exception as e:
        raise ValueError(f"Simulation failed: {str(e)}")


@mcp.tool()
def philbrick_read_signal(port: str) -> dict:
    """Read the current value at a specified port.

    Returns the instantaneous signal value at a component port.
    Port format is "COMPONENT.port" (e.g., "INT1.out").

    Args:
        port: Port to read in format "component_name.port_name"

    Returns:
        dict: The current signal value at the port, plus mini sparkline of recent history if available

    Raises:
        ValueError: If circuit not initialized or port not found
    """
    global _components, _signal_history

    if not _components:
        raise ValueError("Circuit not initialized. Call philbrick_create_circuit first.")

    try:
        comp_name, port_name = parse_port_ref(port)

        component = _components.get(comp_name)
        if component is None:
            raise ValueError(f"Component '{comp_name}' not found")

        # Try input port first, then output port
        patch_point = component.inputs.get(port_name)
        if patch_point is None:
            patch_point = component.outputs.get(port_name)

        if patch_point is None:
            raise ValueError(
                f"Component '{comp_name}' has no port '{port_name}'"
            )

        value = patch_point.read()

        # Get mini sparkline of recent history (last 20 samples) if available
        sparkline = ""
        recent_history = None
        if port in _signal_history and _signal_history[port]:
            recent_history = _signal_history[port][-20:]
            sparkline = _make_sparkline(recent_history, width=20)

        result = {
            "status": "success",
            "port": port,
            "value": value,
            "message": f"Value at '{port}': {value}",
        }

        if sparkline:
            result["recent_sparkline"] = sparkline
            result["recent_samples"] = len(recent_history)

        return result

    except ValueError as e:
        raise ValueError(f"Read failed: {str(e)}")


@mcp.tool()
def philbrick_get_circuit_info() -> dict:
    """Get information about the current circuit.

    Returns lists of all components in the circuit and their connections.

    Returns:
        dict: Components list and connection details

    Raises:
        ValueError: If circuit not initialized
    """
    global _machine, _patchbay, _components

    if _machine is None or _patchbay is None:
        raise ValueError("Circuit not initialized. Call philbrick_create_circuit first.")

    # Build component info
    components_info = []
    for name, component in _components.items():
        components_info.append({
            "name": name,
            "type": component.__class__.__name__,
            "inputs": list(component.inputs.keys()),
            "outputs": list(component.outputs.keys()),
        })

    # Build connection info
    connections_info = []
    for src_port, dst_port in _patchbay.get_connections():
        # Find which components these ports belong to
        src_comp = None
        src_port_name = None
        dst_comp = None
        dst_port_name = None

        for comp_name, comp in _components.items():
            for port_name, port in comp.outputs.items():
                if port is src_port:
                    src_comp = comp_name
                    src_port_name = port_name
            for port_name, port in comp.inputs.items():
                if port is dst_port:
                    dst_comp = comp_name
                    dst_port_name = port_name

        if src_comp and dst_comp:
            connections_info.append({
                "source": f"{src_comp}.{src_port_name}",
                "destination": f"{dst_comp}.{dst_port_name}",
            })

    return {
        "status": "success",
        "time": _machine.time,
        "dt": _machine.dt,
        "components": components_info,
        "components_count": len(_components),
        "connections": connections_info,
        "connections_count": len(connections_info),
    }


@mcp.tool()
def philbrick_get_circuit_diagram() -> dict:
    """Generate ASCII diagram of current circuit topology.

    Creates a text-based representation of the circuit showing all components
    and their connections using box drawing characters and arrows.

    Returns:
        dict: Contains the ASCII diagram as a string and component layout info

    Raises:
        ValueError: If circuit not initialized
    """
    global _machine, _patchbay, _components

    if _machine is None or _patchbay is None:
        raise ValueError("Circuit not initialized. Call philbrick_create_circuit first.")

    if not _components:
        return {
            "status": "success",
            "diagram": "Circuit is empty - no components added yet",
            "message": "No components to diagram",
        }

    try:
        # Build connection map: source_port -> [dest_ports]
        connections_map: dict[tuple, list[tuple]] = {}
        for src_port, dst_port in _patchbay.get_connections():
            # Find which components and ports these belong to
            src_comp = None
            src_port_name = None
            dst_comp = None
            dst_port_name = None

            for comp_name, comp in _components.items():
                for port_name, port in comp.outputs.items():
                    if port is src_port:
                        src_comp = comp_name
                        src_port_name = port_name
                for port_name, port in comp.inputs.items():
                    if port is dst_port:
                        dst_comp = comp_name
                        dst_port_name = port_name

            if src_comp and dst_comp and src_port_name and dst_port_name:
                src_key = (src_comp, src_port_name)
                dst_key = (dst_comp, dst_port_name)
                if src_key not in connections_map:
                    connections_map[src_key] = []
                connections_map[src_key].append(dst_key)

        # Build component display information
        comp_lines = []
        comp_indices = {}

        for idx, (comp_name, component) in enumerate(sorted(_components.items())):
            comp_type = component.__class__.__name__
            input_ports = list(component.inputs.keys())
            output_ports = list(component.outputs.keys())

            # Create component box
            comp_str = f"[{comp_name}: {comp_type}]"
            comp_lines.append(comp_str)
            comp_indices[comp_name] = idx

            # List ports
            if input_ports or output_ports:
                port_str = "  inputs: " + ", ".join(input_ports) if input_ports else ""
                if output_ports:
                    if port_str:
                        port_str += " | outputs: " + ", ".join(output_ports)
                    else:
                        port_str = "  outputs: " + ", ".join(output_ports)
                if port_str:
                    comp_lines.append(port_str)

        # Build connection representation
        conn_lines = []
        if connections_map:
            conn_lines.append("\nConnections:")
            for (src_comp, src_port), destinations in sorted(connections_map.items()):
                for dst_comp, dst_port in destinations:
                    conn_lines.append(f"  {src_comp}.{src_port} ──> {dst_comp}.{dst_port}")

        # Assemble diagram
        diagram_lines = ["Circuit Diagram", "=" * 50, ""]
        diagram_lines.extend(comp_lines)
        diagram_lines.extend(conn_lines)

        diagram = "\n".join(diagram_lines)

        return {
            "status": "success",
            "diagram": diagram,
            "components_count": len(_components),
            "connections_count": len(connections_map),
            "message": f"Circuit diagram generated: {len(_components)} components, {len(connections_map)} connections",
        }

    except Exception as e:
        raise ValueError(f"Failed to generate circuit diagram: {str(e)}")


@mcp.tool()
def philbrick_get_signal_stats(port: str) -> dict:
    """Get statistical information about a signal's history.

    Calculates min, max, mean, final value, and sample count for a port
    that has been recorded during simulation runs. Also includes an ASCII sparkline.

    Args:
        port: Port in format "component_name.port_name"

    Returns:
        dict: Contains min, max, mean, final_value, num_samples, and sparkline for the port

    Raises:
        ValueError: If port not in history or has no samples
    """
    global _signal_history

    if port not in _signal_history:
        raise ValueError(
            f"Port '{port}' not found in signal history. "
            "Run simulation first or port may not be a valid output port."
        )

    history = _signal_history[port]
    if not history:
        raise ValueError(f"No samples recorded for port '{port}'")

    try:
        sparkline = _make_sparkline(history, width=20)
        return {
            "status": "success",
            "port": port,
            "min": min(history),
            "max": max(history),
            "mean": statistics.mean(history),
            "final_value": history[-1],
            "num_samples": len(history),
            "sparkline": sparkline,
        }
    except Exception as e:
        raise ValueError(f"Failed to calculate statistics: {str(e)}")


@mcp.tool()
def philbrick_get_time_series(port: str, last_n: int | None = None) -> dict:
    """Get the time series of values for a signal.

    Returns the recorded signal values for a port, optionally limited to
    the most recent N samples. Includes an ASCII sparkline visualization.

    Args:
        port: Port in format "component_name.port_name"
        last_n: Optional limit to return only the last N samples

    Returns:
        dict: Contains the time series data (list of values), metadata, and sparkline

    Raises:
        ValueError: If port not in history or has no samples
    """
    global _signal_history

    if port not in _signal_history:
        raise ValueError(
            f"Port '{port}' not found in signal history. "
            "Run simulation first or port may not be a valid output port."
        )

    history = _signal_history[port]
    if not history:
        raise ValueError(f"No samples recorded for port '{port}'")

    try:
        # Apply last_n limit if specified
        if last_n is not None:
            if last_n < 1:
                raise ValueError("last_n must be at least 1")
            data = history[-last_n:]
            limited = len(history) > last_n
        else:
            data = history
            limited = False

        # Generate sparkline for the data being returned
        sparkline = _make_sparkline(data, width=20)

        return {
            "status": "success",
            "port": port,
            "values": data,
            "num_samples": len(data),
            "total_samples": len(history),
            "limited": limited,
            "sparkline": sparkline,
            "message": f"Time series for '{port}': {len(data)} samples"
            + (f" (limited from {len(history)} total)" if limited else ""),
        }
    except Exception as e:
        raise ValueError(f"Failed to retrieve time series: {str(e)}")


@mcp.tool()
def philbrick_check_settled(
    port: str, tolerance: float = 0.01, window: int = 10
) -> dict:
    """Check if a signal has settled to a stable value.

    Analyzes the signal history to determine if the last `window` samples
    are within `tolerance` of each other, indicating convergence.

    Args:
        port: Port in format "component_name.port_name"
        tolerance: Maximum allowed variation between samples (default: 0.01)
        window: Number of recent samples to analyze (default: 10)

    Returns:
        dict: Contains settled status, final_value, and variation

    Raises:
        ValueError: If port not in history, has insufficient samples, or invalid parameters
    """
    global _signal_history

    if port not in _signal_history:
        raise ValueError(
            f"Port '{port}' not found in signal history. "
            "Run simulation first or port may not be a valid output port."
        )

    history = _signal_history[port]
    if not history:
        raise ValueError(f"No samples recorded for port '{port}'")

    try:
        # Validate parameters
        if tolerance < 0:
            raise ValueError("tolerance must be non-negative")
        if window < 1:
            raise ValueError("window must be at least 1")

        # Get the last `window` samples
        window_samples = history[-window:] if len(history) >= window else history

        if len(window_samples) < 2:
            # Need at least 2 samples to assess settlement
            return {
                "status": "success",
                "port": port,
                "settled": True,  # Single sample considered settled
                "final_value": window_samples[0],
                "variation": 0.0,
                "samples_analyzed": len(window_samples),
                "message": f"Only {len(window_samples)} sample(s) available",
            }

        # Calculate variation
        min_val = min(window_samples)
        max_val = max(window_samples)
        variation = max_val - min_val

        # Check if settled
        settled = variation <= tolerance

        return {
            "status": "success",
            "port": port,
            "settled": settled,
            "final_value": history[-1],
            "variation": variation,
            "tolerance": tolerance,
            "window": window,
            "samples_analyzed": len(window_samples),
            "message": f"Signal {'is' if settled else 'is not'} settled"
            + f" (variation: {variation:.6f}, tolerance: {tolerance})",
        }
    except ValueError as e:
        raise ValueError(f"Settlement check failed: {str(e)}")


@mcp.tool()
def philbrick_get_phase_portrait(
    x_port: str,
    y_port: str,
    width: int = 50,
    height: int = 20
) -> dict:
    """Generate ASCII phase portrait (x vs y plot) from signal history.

    Great for visualizing oscillators and limit cycles.

    Args:
        x_port: Port for x-axis in format "component_name.port_name"
        y_port: Port for y-axis in format "component_name.port_name"
        width: Width of the ASCII plot in characters (default: 50)
        height: Height of the ASCII plot in characters (default: 20)

    Returns:
        dict: Contains the ASCII art phase portrait and metadata

    Raises:
        ValueError: If ports not in history or have insufficient samples
    """
    global _signal_history

    # Validate ports exist in history
    if x_port not in _signal_history:
        raise ValueError(
            f"Port '{x_port}' not found in signal history. "
            "Run simulation first or port may not be a valid output port."
        )
    if y_port not in _signal_history:
        raise ValueError(
            f"Port '{y_port}' not found in signal history. "
            "Run simulation first or port may not be a valid output port."
        )

    x_history = _signal_history[x_port]
    y_history = _signal_history[y_port]

    if not x_history or not y_history:
        raise ValueError(f"No samples recorded for ports '{x_port}' or '{y_port}'")

    if len(x_history) != len(y_history):
        raise ValueError(
            f"Signal histories have different lengths: "
            f"'{x_port}' has {len(x_history)} samples, "
            f"'{y_port}' has {len(y_history)} samples"
        )

    try:
        # Calculate min/max for scaling
        x_min = min(x_history)
        x_max = max(x_history)
        y_min = min(y_history)
        y_max = max(y_history)

        # Handle case where min equals max (flat signal)
        x_range = x_max - x_min if x_max != x_min else 1.0
        y_range = y_max - y_min if y_max != y_min else 1.0

        # Initialize grid with spaces
        grid = [[' ' for _ in range(width)] for _ in range(height)]

        # Plot points on the grid
        for x_val, y_val in zip(x_history, y_history):
            # Scale values to grid coordinates
            x_idx = int(((x_val - x_min) / x_range) * (width - 1))
            y_idx = int(((y_val - y_min) / y_range) * (height - 1))

            # Clamp to grid boundaries
            x_idx = max(0, min(x_idx, width - 1))
            y_idx = max(0, min(y_idx, height - 1))

            # Y-axis is inverted (top is max, bottom is min)
            y_grid_idx = height - 1 - y_idx

            # Plot point (use filled circle if space available, otherwise dot)
            if grid[y_grid_idx][x_idx] == ' ':
                grid[y_grid_idx][x_idx] = '·'
            else:
                grid[y_grid_idx][x_idx] = '●'

        # Build the ASCII art with axis labels
        lines = []

        # Top y-label
        y_max_str = f"{y_max:.2g}"
        lines.append(f"y={y_max_str:>6} ┤" + ''.join(grid[0]))

        # Middle rows
        for i in range(1, height - 1):
            lines.append(f"       ┤" + ''.join(grid[i]))

        # Bottom y-label and x-axis
        y_min_str = f"{y_min:.2g}"
        lines.append(f"y={y_min_str:>6} ┤" + ''.join(grid[height - 1]))

        # X-axis label line
        x_min_str = f"{x_min:.2g}"
        x_max_str = f"{x_max:.2g}"
        axis_line = "       └" + "─" * width
        lines.append(axis_line)

        # X-axis value labels
        x_label = f"       x={x_min_str:<6} x={x_max_str:>6}"
        lines.append(x_label)

        ascii_art = '\n'.join(lines)

        return {
            "status": "success",
            "x_port": x_port,
            "y_port": y_port,
            "width": width,
            "height": height,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "num_samples": len(x_history),
            "phase_portrait": ascii_art,
            "message": f"Phase portrait generated: {len(x_history)} samples plotted",
        }
    except Exception as e:
        raise ValueError(f"Failed to generate phase portrait: {str(e)}")


if __name__ == "__main__":
    mcp.run()
