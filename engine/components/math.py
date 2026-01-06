import math

from engine.component import Component
from engine.signal import PatchPoint


class Summer(Component):
    """Weighted sum of N inputs."""

    def __init__(self, name: str, weights: list[float] | None = None) -> None:
        super().__init__(name)
        self.weights: list[float] = weights if weights is not None else [1.0, 1.0]

        # Create N inputs based on number of weights
        for i in range(len(self.weights)):
            self.inputs[f"in{i}"] = PatchPoint(f"in{i}")

        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Compute weighted sum: output = sum(input_i * weight_i)."""
        result = 0.0
        for i, weight in enumerate(self.weights):
            input_value = self.inputs[f"in{i}"].read()
            result += input_value * weight
        self.outputs["out"].write(result)

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class Coefficient(Component):
    """Multiply input by a constant coefficient (the 'pot')."""

    def __init__(self, name: str, k: float = 1.0) -> None:
        super().__init__(name)
        self.k: float = k
        self.inputs["in"] = PatchPoint("in")
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Multiply input by coefficient: output = input * k."""
        input_value = self.inputs["in"].read()
        self.outputs["out"].write(input_value * self.k)

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class Inverter(Component):
    """Invert the sign of the input signal (multiply by -1)."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.inputs["in"] = PatchPoint("in")
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Invert input signal: output = -input."""
        input_value = self.inputs["in"].read()
        self.outputs["out"].write(-input_value)

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class Multiplier(Component):
    """Four-quadrant analog multiplier."""

    def __init__(self, name: str, scale: float = 1.0) -> None:
        super().__init__(name)
        self.scale: float = scale
        self.inputs["x"] = PatchPoint("x")
        self.inputs["y"] = PatchPoint("y")
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Multiply inputs with optional scaling: output = x * y * scale."""
        x_value = self.inputs["x"].read()
        y_value = self.inputs["y"].read()
        self.outputs["out"].write(x_value * y_value * self.scale)

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class Comparator(Component):
    """Compare input to threshold."""

    def __init__(
        self, name: str, threshold: float = 0.0, high: float = 1.0, low: float = -1.0
    ) -> None:
        super().__init__(name)
        self.threshold: float = threshold
        self.high: float = high
        self.low: float = low
        self.inputs["in"] = PatchPoint("in")
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Compare input to threshold: output = high if input >= threshold else low."""
        input_value = self.inputs["in"].read()
        self.outputs["out"].write(self.high if input_value >= self.threshold else self.low)

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class Limiter(Component):
    """Clip signal to range."""

    def __init__(self, name: str, min_val: float = -1.0, max_val: float = 1.0) -> None:
        super().__init__(name)
        self.min_val: float = min_val
        self.max_val: float = max_val
        self.inputs["in"] = PatchPoint("in")
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Clamp input to range: output = clamp(input, min_val, max_val)."""
        input_value = self.inputs["in"].read()
        clamped = max(self.min_val, min(self.max_val, input_value))
        self.outputs["out"].write(clamped)

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class Exp(Component):
    """Exponential function."""

    def __init__(self, name: str, scale: float = 1.0) -> None:
        super().__init__(name)
        self.scale: float = scale
        self.inputs["in"] = PatchPoint("in")
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Apply exponential: output = exp(clamp(input * scale, -10, 10))."""
        input_value = self.inputs["in"].read()
        scaled = input_value * self.scale
        clamped = max(-10.0, min(10.0, scaled))
        self.outputs["out"].write(math.exp(clamped))

    def reset(self) -> None:
        """Reset output to one (exp(0) = 1)."""
        self.outputs["out"].write(1.0)


class Divider(Component):
    """Division of two signals."""

    def __init__(self, name: str, epsilon: float = 1e-6) -> None:
        super().__init__(name)
        self.epsilon: float = epsilon
        self.inputs["num"] = PatchPoint("num")
        self.inputs["den"] = PatchPoint("den")
        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Divide numerator by denominator: output = num / max(abs(den), epsilon) * sign(den)."""
        num_value = self.inputs["num"].read()
        den_value = self.inputs["den"].read()
        safe_den = max(abs(den_value), self.epsilon)
        sign_den = 1.0 if den_value >= 0.0 else -1.0
        self.outputs["out"].write(num_value / safe_den * sign_den)

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class DotProduct(Component):
    """N-element dot product of two vectors."""

    def __init__(self, name: str, size: int = 4) -> None:
        super().__init__(name)
        self.size: int = size

        # Create inputs for vector a
        for i in range(self.size):
            self.inputs[f"a{i}"] = PatchPoint(f"a{i}")

        # Create inputs for vector b
        for i in range(self.size):
            self.inputs[f"b{i}"] = PatchPoint(f"b{i}")

        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Compute dot product: output = sum(a_i * b_i for i in range(size))."""
        result = 0.0
        for i in range(self.size):
            a_value = self.inputs[f"a{i}"].read()
            b_value = self.inputs[f"b{i}"].read()
            result += a_value * b_value
        self.outputs["out"].write(result)

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class Max(Component):
    """Maximum of N inputs."""

    def __init__(self, name: str, size: int = 2) -> None:
        super().__init__(name)
        self.size: int = size

        # Create N inputs
        for i in range(self.size):
            self.inputs[f"in{i}"] = PatchPoint(f"in{i}")

        self.outputs["out"] = PatchPoint("out")

    def step(self, dt: float) -> None:
        """Compute maximum: output = max of first size inputs."""
        values = [self.inputs[f"in{i}"].read() for i in range(self.size)]
        self.outputs["out"].write(max(values))

    def reset(self) -> None:
        """Reset output to zero."""
        self.outputs["out"].write(0.0)


class Constant(Component):
    """Output a constant value (no inputs)."""

    def __init__(self, name: str, value: float = 1.0) -> None:
        super().__init__(name)
        self.value: float = value
        self.outputs["out"] = PatchPoint("out")
        # Initialize output immediately
        self.outputs["out"].write(self.value)

    def step(self, dt: float) -> None:
        """Output constant value."""
        self.outputs["out"].write(self.value)

    def reset(self) -> None:
        """Reset output to constant value."""
        self.outputs["out"].write(self.value)
