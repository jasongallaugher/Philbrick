"""Pydantic schema for circuit definitions loaded from YAML.

This module defines the data models for declarative circuit configurations,
supporting the YAML-based circuit definition format.
"""

from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field
import yaml

from engine.machine import Machine
from engine.patchbay import PatchBay
from engine.registry import create_component, COMPONENTS
from engine.subcircuit import (
    SubcircuitDef,
    instantiate_subcircuit,
    load_subcircuit_file,
)
from engine.utils import parse_port_ref


class ComponentDef(BaseModel):
    """Definition of a single component in the circuit.

    Attributes:
        name: Unique identifier for the component instance
        type: Component type (e.g., "Integrator", "Coefficient")
        params: Optional dictionary of component-specific parameters
    """
    name: str
    type: str
    params: Optional[dict[str, Any]] = Field(default_factory=dict)


class PatchDef(BaseModel):
    """Definition of a patch cable connection.

    Represents a connection from one component's output port to another's input port.
    Stored as a two-element list: [source, dest] where each is "component.port".

    Attributes:
        source: Source endpoint as "component_name.port_name"
        dest: Destination endpoint as "component_name.port_name"
    """
    source: str
    dest: str

    @classmethod
    def from_list(cls, patch: list[str]) -> "PatchDef":
        """Create PatchDef from a two-element list [source, dest]."""
        if len(patch) != 2:
            raise ValueError(f"Patch must have exactly 2 elements, got {len(patch)}")
        return cls(source=patch[0], dest=patch[1])


class ChannelDef(BaseModel):
    """Definition of a scope channel for visualization.

    Attributes:
        source: Signal source as "component_name.port_name"
        label: Optional display label for the channel
    """
    source: str
    label: Optional[str] = None


class ScopeDef(BaseModel):
    """Definition of scope channels for circuit visualization.

    Attributes:
        channels: List of channels to display on the scope
    """
    channels: list[ChannelDef] = Field(default_factory=list)


class CircuitDef(BaseModel):
    """Complete circuit definition loaded from YAML.

    Attributes:
        name: Circuit name/identifier
        description: Human-readable circuit description
        components: List of component definitions
        patches: List of patch cable connections
        scope: Scope configuration for visualization
        subcircuits: Dict mapping subcircuit names to their definitions
        imports: List of paths to load subcircuit definitions from
    """
    name: str
    description: str = ""
    components: list[ComponentDef] = Field(default_factory=list)
    patches: list[PatchDef] = Field(default_factory=list)
    scope: Optional[ScopeDef] = None
    subcircuits: dict[str, SubcircuitDef] = Field(default_factory=dict)
    imports: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_path: Optional[str] = None) -> "CircuitDef":
        """Create CircuitDef from parsed YAML dictionary.

        Handles conversion of patch lists to PatchDef objects and
        loading of subcircuit definitions from imports.

        Args:
            data: Parsed YAML dictionary
            base_path: Base path for resolving relative import paths
        """
        # Convert patch lists to PatchDef objects
        if "patches" in data:
            data["patches"] = [
                PatchDef.from_list(p) if isinstance(p, list) else p
                for p in data["patches"]
            ]

        # Convert inline subcircuit dicts to SubcircuitDef objects
        if "subcircuits" in data:
            subcircuits = {}
            for name, subdef in data["subcircuits"].items():
                if isinstance(subdef, dict):
                    subcircuits[name] = SubcircuitDef.from_dict(subdef)
                else:
                    subcircuits[name] = subdef
            data["subcircuits"] = subcircuits

        # Load subcircuits from import paths
        if "imports" in data:
            if "subcircuits" not in data:
                data["subcircuits"] = {}
            for import_path in data["imports"]:
                # Resolve relative paths against base_path
                if base_path and not Path(import_path).is_absolute():
                    import_path = str(Path(base_path) / import_path)
                subdef = load_subcircuit_file(import_path)
                data["subcircuits"][subdef.name] = subdef

        return cls(**data)


class CircuitLoader:
    """Loads circuit definitions from YAML and instantiates components."""

    def __init__(self, machine: Machine, patchbay: PatchBay) -> None:
        """Initialize loader with target machine and patchbay.

        Args:
            machine: Machine to add components to
            patchbay: PatchBay to create connections in
        """
        self.machine = machine
        self.patchbay = patchbay
        # Maps subcircuit instance names to their exposed ports
        self._subcircuit_ports: dict[str, tuple[dict, dict]] = {}

    def load(self, circuit_def: CircuitDef) -> None:
        """Load a circuit definition into the machine and patchbay.

        Components whose type matches a subcircuit name will be instantiated
        as subcircuits. Internal component names are prefixed with the instance
        name (e.g., DIFF1.INT, DIFF1.SUM).

        Args:
            circuit_def: Circuit definition to load
        """
        # Instantiate components and add to machine
        for comp_def in circuit_def.components:
            # Check if this component type is a subcircuit
            if comp_def.type in circuit_def.subcircuits:
                subdef = circuit_def.subcircuits[comp_def.type]
                inputs, outputs = instantiate_subcircuit(
                    subdef,
                    comp_def.name,
                    self.machine,
                    self.patchbay
                )
                self._subcircuit_ports[comp_def.name] = (inputs, outputs)
            elif comp_def.type in COMPONENTS:
                # Regular component type
                component = create_component(
                    comp_def.type,
                    comp_def.name,
                    comp_def.params or {}
                )
                self.machine.add(component)
            else:
                raise ValueError(
                    f"Unknown component type '{comp_def.type}'. "
                    f"Not a registered component or subcircuit."
                )

        # Create patches by looking up component ports
        for patch_def in circuit_def.patches:
            src_port = self._resolve_port(patch_def.source, is_output=True)
            dst_port = self._resolve_port(patch_def.dest, is_output=False)
            self.patchbay.connect(src_port, dst_port)

    def _resolve_port(self, port_ref: str, is_output: bool):
        """Resolve a port reference to a PatchPoint.

        Handles both regular components and subcircuit instances.

        Args:
            port_ref: Port reference in format "component_name.port_name"
            is_output: True if looking for output port, False for input

        Returns:
            The PatchPoint for the specified port

        Raises:
            ValueError: If port not found
        """
        comp_name, port_name = parse_port_ref(port_ref)

        # Check if this is a subcircuit instance
        if comp_name in self._subcircuit_ports:
            inputs, outputs = self._subcircuit_ports[comp_name]
            port_dict = outputs if is_output else inputs
            if port_name in port_dict:
                return port_dict[port_name]
            raise ValueError(
                f"Subcircuit '{comp_name}' has no "
                f"{'output' if is_output else 'input'} port '{port_name}'"
            )

        # Regular component
        component = self._get_component(comp_name)
        port_dict = component.outputs if is_output else component.inputs
        if port_name in port_dict:
            return port_dict[port_name]
        raise ValueError(
            f"Component '{comp_name}' has no "
            f"{'output' if is_output else 'input'} port '{port_name}'"
        )

    def _get_component(self, name: str):
        """Find a component by name.

        Args:
            name: Component name to find

        Returns:
            The component with the given name

        Raises:
            ValueError: If component not found
        """
        for comp in self.machine.components:
            if comp.name == name:
                return comp
        raise ValueError(f"Component '{name}' not found")

    @staticmethod
    def from_yaml(path: str) -> tuple[Machine, PatchBay, CircuitDef]:
        """Load a circuit from a YAML file.

        Args:
            path: Path to the YAML file

        Returns:
            Tuple of (machine, patchbay, circuit_def)
        """
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        # Get the directory containing the YAML file for resolving imports
        base_path = str(Path(path).parent)
        return CircuitLoader.from_dict(data, base_path=base_path)

    @staticmethod
    def from_dict(
        data: dict,
        base_path: Optional[str] = None
    ) -> tuple[Machine, PatchBay, CircuitDef]:
        """Load a circuit from a dictionary (parsed YAML).

        Args:
            data: Dictionary containing circuit definition
            base_path: Base path for resolving relative import paths

        Returns:
            Tuple of (machine, patchbay, circuit_def)
        """
        # Create CircuitDef from the data
        circuit_def = CircuitDef.from_dict(data, base_path=base_path)

        # Create Machine and PatchBay
        machine = Machine(dt=0.001)
        patchbay = PatchBay()

        # Use instance method to do the actual loading
        loader = CircuitLoader(machine, patchbay)
        loader.load(circuit_def)

        return machine, patchbay, circuit_def


class CircuitSaver:
    """Saves circuit state to YAML format."""

    def __init__(self, machine: Machine, patchbay: PatchBay) -> None:
        """Initialize saver with source machine and patchbay.

        Args:
            machine: Machine with components to save
            patchbay: PatchBay with connections to save
        """
        self.machine = machine
        self.patchbay = patchbay

    def to_yaml(
        self,
        path: str,
        name: str = "circuit",
        description: str = ""
    ) -> None:
        """Save a circuit to a YAML file.

        Args:
            path: Output file path
            name: Circuit name
            description: Circuit description
        """
        circuit_dict = self.to_dict(name, description)
        with open(path, 'w') as f:
            yaml.dump(circuit_dict, f, default_flow_style=False, sort_keys=False)

    def to_dict(
        self,
        name: str = "circuit",
        description: str = ""
    ) -> dict:
        """Convert circuit to dictionary (for YAML serialization).

        Args:
            name: Circuit name
            description: Circuit description

        Returns:
            Dictionary containing circuit definition
        """
        # Build component definitions
        components = []
        for comp in self.machine.components:
            comp_type = type(comp).__name__
            params = self._extract_params(comp)

            comp_def = {
                "name": comp.name,
                "type": comp_type
            }

            if params:
                comp_def["params"] = params

            components.append(comp_def)

        # Build patch definitions
        patches = []
        for source_point, dest_point in self.patchbay.get_connections():
            # Find which component owns each patch point
            source_comp = self._find_component_for_point(
                self.machine.components, source_point, is_output=True
            )
            dest_comp = self._find_component_for_point(
                self.machine.components, dest_point, is_output=False
            )

            if source_comp and dest_comp:
                source_ref = f"{source_comp.name}.{source_point.name}"
                dest_ref = f"{dest_comp.name}.{dest_point.name}"
                patches.append([source_ref, dest_ref])

        # Build circuit dictionary
        circuit = {
            "name": name,
            "description": description,
            "components": components,
            "patches": patches
        }

        return circuit

    @staticmethod
    def _extract_params(comp) -> dict[str, Any]:
        """Extract parameters from a component based on its type.

        Args:
            comp: Component to extract parameters from

        Returns:
            Dictionary of parameter names to values
        """
        comp_type = type(comp).__name__
        params = {}

        if comp_type == "Integrator":
            params["initial"] = comp.initial
            params["gain"] = comp.gain
        elif comp_type == "Coefficient":
            params["k"] = comp.k
        elif comp_type == "Summer":
            params["weights"] = comp.weights
        elif comp_type == "VoltageSource":
            params["frequency"] = comp.frequency
            params["amplitude"] = comp.amplitude
        # Inverter has no parameters

        return params

    @staticmethod
    def _find_component_for_point(components, point, is_output: bool):
        """Find which component owns a given patch point.

        Args:
            components: List of components to search
            point: PatchPoint to find
            is_output: True if searching outputs, False for inputs

        Returns:
            Component that owns the point, or None if not found
        """
        for comp in components:
            port_dict = comp.outputs if is_output else comp.inputs
            for port_point in port_dict.values():
                if port_point is point:
                    return comp
        return None
