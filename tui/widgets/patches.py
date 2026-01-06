"""Patch list widget for displaying current patch connections."""

from textual.widgets import Static
from engine.patchbay import PatchBay
from engine.machine import Machine


class PatchList(Static):
    """Widget displaying all current patch connections.

    Shows patches in format "COMPONENT.jack → COMPONENT.jack", or
    "No patches" if the patch bay is empty.
    """

    def __init__(self, patchbay: PatchBay, machine: Machine, **kwargs) -> None:
        """Initialize the patch list widget.

        Args:
            patchbay: Reference to the patch bay for reading connections
            machine: Reference to the machine for looking up component names
            **kwargs: Additional arguments passed to Static
        """
        super().__init__(**kwargs)
        self.patchbay = patchbay
        self.machine = machine

    def render(self) -> str:
        """Render the list of current patch connections.

        Returns:
            String representation of all patches, one per line
        """
        # Access the patch connections via public API
        connections = self.patchbay.get_connections()

        if not connections:
            return "No patches"

        lines = []
        for source_point, dest_point in connections:
            # Find component names by matching patch points
            source_comp_name = self._find_component_name(source_point, is_output=True)
            dest_comp_name = self._find_component_name(dest_point, is_output=False)

            # Format: SOURCE.jack → DEST.jack
            line = f"{source_comp_name}.{source_point.name} → {dest_comp_name}.{dest_point.name}"
            lines.append(line)

        return "\n".join(lines)

    def _find_component_name(self, patch_point, is_output: bool) -> str:
        """Find the component name that owns a given patch point.

        Args:
            patch_point: The patch point to search for
            is_output: True if searching outputs, False if searching inputs

        Returns:
            Component name, or "?" if not found
        """
        for component in self.machine.components:
            points_dict = component.outputs if is_output else component.inputs
            for point in points_dict.values():
                if point is patch_point:
                    return component.name
        return "?"
