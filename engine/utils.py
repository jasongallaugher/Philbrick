"""Shared utility functions for the engine module."""


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
    parts = port_ref.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid port reference '{port_ref}'. "
            f"Expected format: 'component_name.port_name'"
        )
    return parts[0], parts[1]
