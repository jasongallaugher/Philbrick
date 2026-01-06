"""ASCII Scope widget for displaying waveforms."""

from textual.widgets import Static
from textual.reactive import reactive

from engine.signal import PatchPoint, Signal


class Channel:
    """Container for a single channel's data and configuration."""

    def __init__(
        self,
        source: PatchPoint | Signal | None = None,
        label: str = "",
        char: str = "●",
    ) -> None:
        """Initialize a channel.

        Args:
            source: Signal source to sample from.
            label: Display label for this channel.
            char: Character to use when rendering this channel.
        """
        self.source = source
        self.label = label
        self.char = char
        self.buffer: list[float] = []


class Scope(Static):
    """ASCII art waveform display widget.

    Displays waveforms from multiple channels as ASCII art with box-drawing
    characters. Configurable Y-axis voltage scale and X-axis sample range.
    Supports up to multiple channels with different display characters.
    """

    DEFAULT_CSS = """
    Scope {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
    }
    """

    # Channel characters (solid and hollow for visual distinction)
    CHANNEL_CHARS = ["●", "○", "◆", "◇", "■", "□", "▲", "△"]

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
            samples: List of float samples to display (legacy, used for channel 0).
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

        # Legacy single-channel support
        self._buffer: list[float] = list(self.samples)
        self.source: PatchPoint | Signal | None = None

        # Multi-channel support
        self.channels: list[Channel] = []

    def set_source(self, source: PatchPoint | Signal) -> None:
        """Attach a signal source to sample from (legacy single-channel mode).

        For backward compatibility, this sets channel 0. If no channels exist,
        one is created. If channels exist, channel 0 is updated.

        Args:
            source: Signal source to sample from.
        """
        self.source = source

        # Update or create channel 0 for backward compatibility
        if len(self.channels) == 0:
            self.add_channel(source, label="CH1")
        else:
            self.channels[0].source = source

    def add_channel(
        self, source: PatchPoint | Signal, label: str | None = None
    ) -> None:
        """Add a new channel to the scope.

        Args:
            source: Signal source to sample from.
            label: Display label for this channel. If None, defaults to "CHn".
        """
        channel_num = len(self.channels) + 1
        if label is None:
            label = f"CH{channel_num}"

        char = self.CHANNEL_CHARS[len(self.channels) % len(self.CHANNEL_CHARS)]
        channel = Channel(source=source, label=label, char=char)
        self.channels.append(channel)

    def clear_channels(self) -> None:
        """Remove all channels from the scope."""
        self.channels.clear()
        self.source = None

    def capture_sample(self) -> None:
        """Read a sample from all channel sources into their buffers.

        Also maintains legacy single-channel buffer for backward compatibility.
        """
        # Legacy single-channel mode
        if self.source is not None:
            self._buffer.append(self.source.read())
            if len(self._buffer) > self.max_samples:
                self._buffer.pop(0)

        # Multi-channel mode
        for channel in self.channels:
            if channel.source is not None:
                channel.buffer.append(channel.source.read())
                if len(channel.buffer) > self.max_samples:
                    channel.buffer.pop(0)

    def flush(self) -> None:
        """Copy buffered samples to the reactive list for rendering.

        In multi-channel mode, this copies channel 0's buffer (if it exists)
        to maintain backward compatibility with the reactive samples property.
        """
        if self.channels:
            # Use channel 0's buffer for the reactive property
            self.samples = self.channels[0].buffer.copy()
        else:
            # Legacy single-channel mode
            self.samples = self._buffer.copy()

    def set_samples(self, samples: list[float]) -> None:
        """Update the waveform data (legacy single-channel mode).

        Args:
            samples: List of float samples.
        """
        self._buffer = list(samples)
        self.samples = list(samples)

        # Also update channel 0 if it exists
        if self.channels:
            self.channels[0].buffer = list(samples)

    def _render_channel(
        self,
        channel: Channel,
        canvas: list[list[str]],
        width: int,
        height: int,
        y_range: float,
    ) -> None:
        """Render a single channel onto the canvas.

        Args:
            channel: The channel to render.
            canvas: The 2D canvas to draw on.
            width: Canvas width.
            height: Canvas height.
            y_range: Voltage range for normalization.
        """
        if not channel.buffer:
            return

        samples_per_pixel = max(1, self.samples_per_pixel)
        window_size = width * samples_per_pixel

        # Always take the most recent samples (scrolling window)
        window = (
            channel.buffer[-window_size:]
            if len(channel.buffer) > window_size
            else channel.buffer
        )

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

            # Draw point character (overlay on existing canvas)
            if x_idx < width and y_pos < height:
                # Allow multiple channels to overlap
                if canvas[y_pos][x_idx] == " " or canvas[y_pos][x_idx] == "─":
                    canvas[y_pos][x_idx] = channel.char

    def render(self) -> str:
        """Render the waveform as ASCII art with multi-channel support.

        Returns:
            ASCII string representation of the waveform(s).
        """
        # Determine which data source to use
        has_channel_data = any(len(ch.buffer) > 0 for ch in self.channels)
        has_legacy_data = len(self.samples) > 0

        if not has_channel_data and not has_legacy_data:
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
        canvas = [[" " for _ in range(width)] for _ in range(height)]

        # Y-axis labels and grid
        y_range = self.v_max - self.v_min
        if y_range == 0:
            y_range = 1.0

        # Draw 0V center line if in range (do this first so channels overlay on top)
        if self.v_min <= 0 <= self.v_max:
            center_y = int((1.0 - (0 - self.v_min) / y_range) * (height - 1))
            if 0 <= center_y < height:
                for x in range(width):
                    canvas[center_y][x] = "─"

        # Render all channels (multi-channel mode)
        if self.channels:
            for channel in self.channels:
                self._render_channel(channel, canvas, width, height, y_range)
        else:
            # Legacy single-channel mode
            if self.samples:
                legacy_channel = Channel(source=None, label="CH1", char="●")
                legacy_channel.buffer = self.samples
                self._render_channel(legacy_channel, canvas, width, height, y_range)

        # Add Y-axis labels on the left
        max_label_width = max(
            len(f"+{self.v_max:.1f}V"),
            len(f"{self.v_min:.1f}V"),
            len(" 0V"),
        )

        result_lines = []

        # Add legend at the top if we have channels
        if self.channels:
            legend_parts = []
            for channel in self.channels:
                legend_parts.append(f"{channel.label} {channel.char}")
            legend = "  ".join(legend_parts)
            result_lines.append(legend)
            result_lines.append("")  # Blank line after legend

        for y_idx in range(height):
            line = "".join(canvas[y_idx])

            # Add voltage labels at top, middle (0V), and bottom
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

        return "\n".join(result_lines)
