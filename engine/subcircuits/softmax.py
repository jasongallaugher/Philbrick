"""Softmax subcircuit for computing softmax normalization of 2 inputs.

Implements: softmax(x0, x1) = [exp(x0) / (exp(x0) + exp(x1)), exp(x1) / (exp(x0) + exp(x1))]
"""

from engine.subcircuit import SubcircuitDef, ComponentDef, PatchDef
from engine.registry import register_subcircuit


def create_softmax_def() -> SubcircuitDef:
    """Create and return a Softmax subcircuit definition.

    The softmax subcircuit computes the softmax normalization for 2 inputs:
    - Applies exponential to each input
    - Sums the exponentials
    - Divides each exponential by the sum

    Returns:
        SubcircuitDef: A fully configured softmax subcircuit

    Example:
        >>> softmax_def = create_softmax_def()
        >>> softmax_def.name
        'Softmax'
        >>> softmax_def.inputs
        ['in0', 'in1']
        >>> softmax_def.outputs
        ['out0', 'out1']
    """
    return SubcircuitDef(
        name="Softmax",
        description="Softmax normalization for 2 inputs: exp(x_i) / sum(exp(x_j))",
        inputs=["in0", "in1"],
        outputs=["out0", "out1"],
        components=[
            # Exponential components for each input
            ComponentDef(name="EXP0", type="Exp", params={}),
            ComponentDef(name="EXP1", type="Exp", params={}),
            # Summer to compute sum of exponentials
            ComponentDef(name="SUM", type="Summer", params={"weights": [1.0, 1.0]}),
            # Dividers for softmax outputs
            ComponentDef(name="DIV0", type="Divider", params={}),
            ComponentDef(name="DIV1", type="Divider", params={}),
        ],
        patches=[
            # Internal wiring only - input/output routing handled by maps
            # Feed exponentials into summer
            PatchDef(source="EXP0.out", dest="SUM.in0"),
            PatchDef(source="EXP1.out", dest="SUM.in1"),
            # Feed exponentials and sum to dividers
            PatchDef(source="EXP0.out", dest="DIV0.num"),
            PatchDef(source="SUM.out", dest="DIV0.den"),
            PatchDef(source="EXP1.out", dest="DIV1.num"),
            PatchDef(source="SUM.out", dest="DIV1.den"),
        ],
        input_map={
            "in0": "EXP0.in",
            "in1": "EXP1.in",
        },
        output_map={
            "out0": "DIV0.out",
            "out1": "DIV1.out",
        },
    )


def register_softmax() -> None:
    """Register the Softmax subcircuit with the component registry.

    Adds the Softmax subcircuit definition to the registry so it can be
    instantiated using the standard component creation pipeline.

    Example:
        >>> register_softmax()
        >>> # Softmax is now available as a component type
    """
    softmax_def = create_softmax_def()
    register_subcircuit("Softmax", softmax_def)
