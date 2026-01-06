"""Subcircuit (macro) support for reusable circuit blocks.

This module provides the ability to define reusable circuit blocks that can be
instantiated multiple times with different names. Each subcircuit encapsulates
a set of components and internal patches, exposing only specified input and
output ports.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field

from engine.component import Component
from engine.machine import Machine
from engine.patchbay import PatchBay
from engine.signal import PatchPoint


class ComponentDef(BaseModel):
    """Definition of a single component in a subcircuit.

    Attributes:
        name: Unique identifier for the component instance (within subcircuit)
        type: Component type (e.g., "Integrator", "Coefficient")
        params: Optional dictionary of component-specific parameters
    """
    name: str
    type: str
    params: Optional[dict[str, Any]] = Field(default_factory=dict)


class PatchDef(BaseModel):
    """Definition of a patch cable connection within a subcircuit.

    Represents a connection from one component's output port to another's input port.

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


class PortMapping(BaseModel):
    """Maps an exposed port name to an internal component port.

    Attributes:
        external: The exposed port name (e.g., "in", "out")
        internal: The internal component port (e.g., "SUM.in0", "INT.out")
    """
    external: str
    internal: str


class SubcircuitDef(BaseModel):
    """Definition of a reusable circuit block (macro).

    A subcircuit encapsulates a set of components and their internal connections,
    exposing only specified input and output ports. When instantiated, all internal
    component names are prefixed with the instance name.

    Attributes:
        name: Unique identifier for this subcircuit type
        description: Human-readable description of the subcircuit's function
        inputs: List of exposed input port names
        outputs: List of exposed output port names
        components: List of component definitions within the subcircuit
        patches: List of internal patch connections
        input_map: Optional mapping of input port names to internal component ports
        output_map: Optional mapping of output port names to internal component ports
    """
    name: str
    description: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    components: list[ComponentDef] = Field(default_factory=list)
    patches: list[PatchDef] = Field(default_factory=list)
    # Port mappings: map exposed port names to internal component.port references
    input_map: dict[str, str] = Field(default_factory=dict)
    output_map: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubcircuitDef":
        """Create SubcircuitDef from parsed YAML dictionary.

        Handles conversion of patch lists to PatchDef objects and
        component dicts to ComponentDef objects.
        """
        # Convert patch lists to PatchDef objects
        if "patches" in data:
            data["patches"] = [
                PatchDef.from_list(p) if isinstance(p, list) else
                (PatchDef(**p) if isinstance(p, dict) else p)
                for p in data["patches"]
            ]

        # Convert component dicts to ComponentDef objects
        if "components" in data:
            data["components"] = [
                ComponentDef(**c) if isinstance(c, dict) else c
                for c in data["components"]
            ]

        return cls(**data)


class SubcircuitComponent(Component):
    """A component that is itself a subcircuit (macro).

    When instantiated, this component creates all internal components defined
    in its subcircuit definition, sets up internal patches, and exposes only
    the specified input and output ports.

    Attributes:
        definition: The SubcircuitDef that defines this subcircuit's structure
        machine: Reference to the Machine for adding internal components
        patchbay: Reference to the PatchBay for creating internal patches
    """

    def __init__(
        self,
        name: str,
        definition: SubcircuitDef,
        machine: Machine,
        patchbay: PatchBay,
    ) -> None:
        """Initialize a SubcircuitComponent.

        Args:
            name: Instance name for this subcircuit
            definition: SubcircuitDef defining the subcircuit structure
            machine: Machine to add internal components to
            patchbay: PatchBay to create internal patches in
        """
        super().__init__(name)
        self.definition = definition
        self.machine = machine
        self.patchbay = patchbay

        # Instantiate the subcircuit and expose its ports
        exposed_inputs, exposed_outputs = instantiate_subcircuit(
            definition, name, machine, patchbay
        )
        self.inputs = exposed_inputs
        self.outputs = exposed_outputs

    def step(self, dt: float) -> None:
        """Subcircuit components are passive containers.

        They don't perform any computation themselves; their internal
        components handle all simulation steps.
        """
        pass

    def reset(self) -> None:
        """Reset the subcircuit (no-op for container).

        Internal components maintain their own state and are reset
        independently as part of the machine's reset.
        """
        pass


def parse_port_ref(port_ref: str) -> tuple[str, str]:
    """Parse a port reference string into component and port names.

    Args:
        port_ref: Port reference in format "component_name.port_name"

    Returns:
        Tuple of (component_name, port_name)

    Raises:
        ValueError: If port reference format is invalid

    Example:
        >>> parse_port_ref("INT1.out")
        ('INT1', 'out')
    """
    parts = port_ref.split(".", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid port reference '{port_ref}'. "
            f"Expected format: 'component_name.port_name'"
        )
    return parts[0], parts[1]


def instantiate_subcircuit(
    subcircuit_def: SubcircuitDef,
    instance_name: str,
    machine: Machine,
    patchbay: PatchBay
) -> tuple[dict[str, PatchPoint], dict[str, PatchPoint]]:
    """Instantiate a subcircuit, returning its exposed input and output ports.

    Creates all internal components with prefixed names (instance_name.component_name),
    sets up internal patches, and returns dictionaries mapping exposed port names
    to their corresponding PatchPoints.

    Args:
        subcircuit_def: The subcircuit definition to instantiate
        instance_name: Name prefix for all internal components
        machine: Machine to add components to
        patchbay: PatchBay to create internal connections in

    Returns:
        Tuple of (input_ports, output_ports) where each is a dict mapping
        exposed port names to PatchPoint objects.

    Example:
        >>> inputs, outputs = instantiate_subcircuit(diff_def, "DIFF1", machine, patchbay)
        >>> # inputs["in"] is the PatchPoint for DIFF1's input
        >>> # outputs["out"] is the PatchPoint for DIFF1's output
    """
    # Import here to avoid circular import with registry
    from engine.registry import create_component

    # Track created components by their local (unprefixed) names
    local_components: dict[str, Any] = {}

    # 1. Instantiate all internal components with prefixed names
    for comp_def in subcircuit_def.components:
        prefixed_name = f"{instance_name}.{comp_def.name}"
        component = create_component(
            comp_def.type,
            prefixed_name,
            comp_def.params or {}
        )
        machine.add(component)
        local_components[comp_def.name] = component

    # 2. Create internal patches
    for patch_def in subcircuit_def.patches:
        src_comp_name, src_port_name = parse_port_ref(patch_def.source)
        dst_comp_name, dst_port_name = parse_port_ref(patch_def.dest)

        src_component = local_components.get(src_comp_name)
        dst_component = local_components.get(dst_comp_name)

        if src_component is None:
            raise ValueError(
                f"Subcircuit '{subcircuit_def.name}' patch references "
                f"unknown component '{src_comp_name}'"
            )
        if dst_component is None:
            raise ValueError(
                f"Subcircuit '{subcircuit_def.name}' patch references "
                f"unknown component '{dst_comp_name}'"
            )

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

        patchbay.connect(src_port, dst_port)

    # 3. Map exposed input ports to internal component inputs
    exposed_inputs: dict[str, PatchPoint] = {}
    for input_name in subcircuit_def.inputs:
        if input_name in subcircuit_def.input_map:
            # Use explicit mapping
            internal_ref = subcircuit_def.input_map[input_name]
            comp_name, port_name = parse_port_ref(internal_ref)
            component = local_components.get(comp_name)
            if component is None:
                raise ValueError(
                    f"Input mapping references unknown component '{comp_name}'"
                )
            port = component.inputs.get(port_name)
            if port is None:
                raise ValueError(
                    f"Component '{comp_name}' has no input port '{port_name}'"
                )
            exposed_inputs[input_name] = port
        else:
            # Try to find a component with a matching input port name
            # This is a convenience for simple cases
            found = False
            for comp in local_components.values():
                if input_name in comp.inputs:
                    exposed_inputs[input_name] = comp.inputs[input_name]
                    found = True
                    break
            if not found:
                raise ValueError(
                    f"Could not find input port '{input_name}' in subcircuit "
                    f"'{subcircuit_def.name}'. Use input_map to specify mapping."
                )

    # 4. Map exposed output ports to internal component outputs
    exposed_outputs: dict[str, PatchPoint] = {}
    for output_name in subcircuit_def.outputs:
        if output_name in subcircuit_def.output_map:
            # Use explicit mapping
            internal_ref = subcircuit_def.output_map[output_name]
            comp_name, port_name = parse_port_ref(internal_ref)
            component = local_components.get(comp_name)
            if component is None:
                raise ValueError(
                    f"Output mapping references unknown component '{comp_name}'"
                )
            port = component.outputs.get(port_name)
            if port is None:
                raise ValueError(
                    f"Component '{comp_name}' has no output port '{port_name}'"
                )
            exposed_outputs[output_name] = port
        else:
            # Try to find a component with a matching output port name
            found = False
            for comp in local_components.values():
                if output_name in comp.outputs:
                    exposed_outputs[output_name] = comp.outputs[output_name]
                    found = True
                    break
            if not found:
                raise ValueError(
                    f"Could not find output port '{output_name}' in subcircuit "
                    f"'{subcircuit_def.name}'. Use output_map to specify mapping."
                )

    return exposed_inputs, exposed_outputs


def load_subcircuit_file(path: str) -> SubcircuitDef:
    """Load a subcircuit definition from a YAML file.

    Args:
        path: Path to the YAML file

    Returns:
        SubcircuitDef loaded from the file
    """
    import yaml
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return SubcircuitDef.from_dict(data)
