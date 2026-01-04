"""ASCII Scope widget for displaying waveforms."""

from textual.widgets import Static
from textual.reactive import reactive

from engine.signal import PatchPoint, Signal


class Scope(Static):
    """ASCII art waveform display widget.

    Displays a list of float samples as an ASCII waveform with box-drawing
    characters. Configurable Y-axis voltage scale and X-axis sample range.
    """

    DEFAULT_CSS = """
    Scope {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
    }
    """

    samples: reactive[list[float]] = reactive([])
    v_min: float = -1.0
    v_max: float = 1.0

    def __init__(
        self,
        samples: list[float] | None = None,
        v_min: float = -1.0,
        v_max: float = 1.0,
        *,
        width: int = 60,
        height: int = 11,
        max_samples: int = 200,
        samples_per_pixel: int = 1,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize Scope widget.

        Args:
            samples: List of float samples to display.
            v_min: Minimum voltage for Y-axis (default -1.0).
            v_max: Maximum voltage for Y-axis (default +1.0).
            width: Display width in characters (default 60).
            height: Display height in characters (default 11).
            max_samples: Rolling buffer size for samples.
            samples_per_pixel: Samples represented by each column (timebase).
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self.samples = list(samples) if samples is not None else []
        self.v_min = v_min
        self.v_max = v_max
        self.display_width = width
        self.display_height = height
        self.max_samples = max_samples
        self.samples_per_pixel = samples_per_pixel
        self._buffer: list[float] = list(self.samples)
        self.source: PatchPoint | Signal | None = None

    def set_source(self, source: PatchPoint | Signal) -> None:
        """Attach a signal source to sample from."""
        self.source = source

    def capture_sample(self) -> None:
        """Read a sample from the attached source into the buffer."""
        if self.source is None:
            return
        self._buffer.append(self.source.read())
        if len(self._buffer) > self.max_samples:
            self._buffer.pop(0)

    def flush(self) -> None:
        """Copy buffered samples to the reactive list for rendering."""
        self.samples = self._buffer.copy()

    def set_samples(self, samples: list[float]) -> None:
        """Update the waveform data.

        Args:
            samples: List of float samples.
        """
        self._buffer = list(samples)
        self.samples = list(samples)

    def render(self) -> str:
        """Render the waveform as ASCII art.

        Returns:
            ASCII string representation of the waveform.
        """
        if not self.samples:
            return "No data"

        # Use widget size if mounted and reasonable, otherwise use explicit dimensions
        try:
            w = self.size.width - 8
            h = self.size.height
            if w > 10 and h > 5:
                width = w
                height = h
            else:
                width = self.display_width
                height = self.display_height
        except (AttributeError, TypeError):
            width = self.display_width
            height = self.display_height

        # Create canvas
        canvas = [[' ' for _ in range(width)] for _ in range(height)]

        # Y-axis labels and grid
        y_range = self.v_max - self.v_min
        if y_range == 0:
            y_range = 1.0

        # Draw samples as point characters with a fixed timebase
        samples_per_pixel = max(1, self.samples_per_pixel)
        window_size = width * samples_per_pixel
        
        # Always take the most recent samples (scrolling window)
        window = self.samples[-window_size:] if len(self.samples) > window_size else self.samples

        samples_to_draw: list[float | None] = []
        num_samples = len(window)
        
        for x_idx in range(width):
            start = x_idx * samples_per_pixel
            end = start + samples_per_pixel
            
            # Skip if this bucket is beyond available samples
            if start >= num_samples:
                samples_to_draw.append(None)
                continue
                
            # Clip the end to available samples
            end = min(end, num_samples)
            bucket = window[start:end]
            
            # Use the last (most recent) value in the bucket
            sample_value = None
            for value in reversed(bucket):
                if value is not None:
                    sample_value = value
                    break
            samples_to_draw.append(sample_value)

        for x_idx, sample in enumerate(samples_to_draw):
            if sample is None:
                continue
            # Normalize sample to 0-1 range
            normalized = (sample - self.v_min) / y_range
            normalized = max(0.0, min(1.0, normalized))

            # Convert to Y position (top of canvas is max, bottom is min)
            y_pos = int((1.0 - normalized) * (height - 1))
            y_pos = max(0, min(height - 1, y_pos))

            # Draw point character
            if x_idx < width and y_pos < height:
                char = '●'
                canvas[y_pos][x_idx] = char

        # Draw smooth 0V center line if in range
        if self.v_min <= 0 <= self.v_max:
            center_y = int((1.0 - (0 - self.v_min) / y_range) * (height - 1))
            if 0 <= center_y < height:
                for x in range(width):
                    if canvas[center_y][x] == ' ':
                        canvas[center_y][x] = '─'
                    elif canvas[center_y][x] == '●':
                        # Keep the point if it's on the center line
                        pass

        # Add Y-axis labels on the left
        # Determine max label width to ensure alignment
        max_label_width = max(
            len(f"+{self.v_max:.1f}V"),
            len(f"{self.v_min:.1f}V"),
            len(" 0V"),
        )
        
        result_lines = []
        for y_idx in range(height):
            line = ''.join(canvas[y_idx])

            # Add voltage labels at top, middle (0V), and bottom
            voltage = self.v_max - (y_idx / (height - 1)) * y_range
            if y_idx == 0:
                # Top label
                label = f"+{self.v_max:.1f}V"
            elif self.v_min <= 0 <= self.v_max:
                center_y = int((1.0 - (0 - self.v_min) / y_range) * (height - 1))
                if y_idx == center_y:
                    # Middle label at 0V
                    label = " 0V"
                elif y_idx == height - 1:
                    # Bottom label
                    label = f"{self.v_min:.1f}V"
                else:
                    label = ""
            else:
                # Handle case where 0V is not in range
                if y_idx == height - 1:
                    label = f"{self.v_min:.1f}V"
                else:
                    label = ""
            
            # Pad label to fixed width for alignment
            label = label.rjust(max_label_width)

            result_lines.append(f"{label} ┤ {line}")

        return '\n'.join(result_lines)
