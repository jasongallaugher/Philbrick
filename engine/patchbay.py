"""Patch bay for connecting analog computer components."""

from engine.signal import PatchPoint


class PatchBay:
    """Manages patch connections between output and input points.

    A patch bay allows connecting output patch points to input patch points,
    with support for fan-out (one output to multiple inputs). Signal values
    are propagated through all connections during the propagate step.
    """

    def __init__(self) -> None:
        """Initialize an empty patch bay."""
        self._connections: list[tuple[PatchPoint, PatchPoint]] = []

    def connect(self, source: PatchPoint, dest: PatchPoint) -> None:
        """Create a patch connection from source output to dest input.

        Args:
            source: Output patch point to read from
            dest: Input patch point to write to
        """
        connection = (source, dest)
        if connection not in self._connections:
            self._connections.append(connection)

    def disconnect(self, source: PatchPoint, dest: PatchPoint) -> None:
        """Remove a patch connection.

        Args:
            source: Output patch point
            dest: Input patch point
        """
        connection = (source, dest)
        if connection in self._connections:
            self._connections.remove(connection)

    def clear(self) -> None:
        """Remove all patch connections."""
        self._connections.clear()

    def propagate(self) -> None:
        """Propagate signal values through all patch connections.

        Copies the value from each source output to its connected destination
        input(s). This should be called during each simulation step to update
        all patched signals.
        """
        for source, dest in self._connections:
            value = source.read()
            dest.write(value)
