#!/usr/bin/env python3
"""Headless CLI runner for the Philbrick analog computer simulator.

This module provides a command-line interface for running circuit simulations
without the TUI, useful for batch processing and data collection.

Example usage:
    python cli.py circuits/harmonic.yaml --steps 5000 --output data.csv
    python cli.py circuits/harmonic.yaml --steps 1000 --quiet
"""

import argparse
import csv
import sys
from pathlib import Path

from engine.circuit import CircuitLoader, parse_port_ref


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace
    """
    parser = argparse.ArgumentParser(
        description="Run Philbrick analog computer simulations from YAML circuit files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py circuits/harmonic.yaml --steps 5000 --output data.csv
  python cli.py circuits/harmonic.yaml --steps 1000 --quiet
  python cli.py circuits/damped.yaml --dt 0.0001 --steps 10000
        """,
    )

    parser.add_argument(
        "circuit_file",
        type=str,
        help="Path to YAML circuit file",
    )

    parser.add_argument(
        "--steps",
        "-n",
        type=int,
        default=1000,
        metavar="N",
        help="Number of simulation steps to run (default: 1000)",
    )

    parser.add_argument(
        "--dt",
        type=float,
        default=0.001,
        metavar="FLOAT",
        help="Timestep in seconds (default: 0.001)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        metavar="FILE",
        help="Output file for results (CSV format)",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )

    return parser.parse_args()


def get_channel_value(machine, channel_source: str) -> float:
    """Get the current value of a scope channel source.

    Args:
        machine: Machine instance with components
        channel_source: Source string in format "component_name.port_name"

    Returns:
        Current value at the specified port
    """
    comp_name, port_name = parse_port_ref(channel_source)

    # Find the component by name
    for comp in machine.components:
        if comp.name == comp_name:
            # Check outputs first (most common for scope channels)
            if port_name in comp.outputs:
                return comp.outputs[port_name].read()
            # Fall back to inputs
            if port_name in comp.inputs:
                return comp.inputs[port_name].read()
            raise ValueError(f"Port '{port_name}' not found on component '{comp_name}'")

    raise ValueError(f"Component '{comp_name}' not found")


def run_simulation(
    circuit_file: str,
    steps: int,
    dt: float,
    output_file: str | None,
    quiet: bool,
) -> None:
    """Run the simulation and output results.

    Args:
        circuit_file: Path to YAML circuit file
        steps: Number of simulation steps
        dt: Timestep in seconds
        output_file: Optional CSV output file path
        quiet: If True, suppress progress output
    """
    # Validate circuit file exists
    circuit_path = Path(circuit_file)
    if not circuit_path.exists():
        print(f"Error: Circuit file not found: {circuit_file}", file=sys.stderr)
        sys.exit(1)

    # Load circuit from YAML
    if not quiet:
        print(f"Loading circuit from {circuit_file}...")

    try:
        machine, patchbay, circuit_def = CircuitLoader.from_yaml(circuit_file)
    except Exception as e:
        print(f"Error loading circuit: {e}", file=sys.stderr)
        sys.exit(1)

    # Override machine timestep with CLI argument
    machine.dt = dt

    # Get scope channel definitions
    channels = []
    channel_labels = []
    if circuit_def.scope and circuit_def.scope.channels:
        for ch in circuit_def.scope.channels:
            channels.append(ch.source)
            channel_labels.append(ch.label or ch.source)

    if not quiet:
        print(f"Circuit: {circuit_def.name}")
        if circuit_def.description:
            print(f"Description: {circuit_def.description}")
        print(f"Components: {len(machine.components)}")
        print(f"Patches: {len(patchbay._connections)}")
        print(f"Scope channels: {len(channels)}")
        print(f"Running {steps} steps with dt={dt}s...")

    # Collect data for each step
    data = []

    # Initialize min/max tracking for summary
    if channels:
        min_values = [float('inf')] * len(channels)
        max_values = [float('-inf')] * len(channels)
    else:
        min_values = []
        max_values = []

    # Progress reporting interval
    progress_interval = max(1, steps // 10)

    # Run simulation
    for step in range(steps):
        # Propagate signals through patches
        patchbay.propagate()

        # Step all components
        machine.step()

        # Collect channel values
        if channels:
            values = []
            for i, ch_source in enumerate(channels):
                try:
                    val = get_channel_value(machine, ch_source)
                    values.append(val)
                    min_values[i] = min(min_values[i], val)
                    max_values[i] = max(max_values[i], val)
                except ValueError as e:
                    if not quiet:
                        print(f"Warning: {e}", file=sys.stderr)
                    values.append(0.0)

            data.append({
                "step": step,
                "time": machine.time,
                "values": values,
            })

        # Progress reporting
        if not quiet and (step + 1) % progress_interval == 0:
            percent = ((step + 1) / steps) * 100
            print(f"  Progress: {percent:.0f}% ({step + 1}/{steps} steps)")

    if not quiet:
        print("Simulation complete.")

    # Output results
    if output_file:
        # Write CSV file
        write_csv(output_file, channel_labels, data)
        if not quiet:
            print(f"Results written to {output_file}")
    else:
        # Print summary
        print_summary(channel_labels, data, min_values, max_values)


def write_csv(
    output_file: str,
    channel_labels: list[str],
    data: list[dict],
) -> None:
    """Write simulation results to CSV file.

    Args:
        output_file: Output file path
        channel_labels: List of channel label strings
        data: List of data dictionaries with step, time, and values
    """
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)

        # Write header
        header = ["step", "time"] + channel_labels
        writer.writerow(header)

        # Write data rows
        for row in data:
            csv_row = [row["step"], row["time"]] + row["values"]
            writer.writerow(csv_row)


def print_summary(
    channel_labels: list[str],
    data: list[dict],
    min_values: list[float],
    max_values: list[float],
) -> None:
    """Print summary of simulation results.

    Args:
        channel_labels: List of channel label strings
        data: List of data dictionaries with step, time, and values
        min_values: Minimum value for each channel
        max_values: Maximum value for each channel
    """
    print("\n" + "=" * 50)
    print("Simulation Summary")
    print("=" * 50)

    if not data:
        print("No data collected (no scope channels defined)")
        return

    final_row = data[-1]
    print(f"\nFinal time: {final_row['time']:.6f}s")
    print(f"Total steps: {final_row['step'] + 1}")

    if channel_labels:
        print("\nChannel Results:")
        print("-" * 50)
        print(f"{'Channel':<20} {'Final':>10} {'Min':>10} {'Max':>10}")
        print("-" * 50)

        for i, label in enumerate(channel_labels):
            final_val = final_row["values"][i]
            min_val = min_values[i]
            max_val = max_values[i]
            print(f"{label:<20} {final_val:>10.4f} {min_val:>10.4f} {max_val:>10.4f}")

        print("-" * 50)


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args()

    run_simulation(
        circuit_file=args.circuit_file,
        steps=args.steps,
        dt=args.dt,
        output_file=args.output,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
