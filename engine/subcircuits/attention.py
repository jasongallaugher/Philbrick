"""AttentionHead subcircuit for computing single-query attention.

Implements: output = (q · k) * v

A simple single-query attention mechanism:
1. Computes dot product of query and key vectors: score = q · k
2. Passes score through a coefficient (placeholder for future multi-key softmax)
3. Multiplies the weighted score by the value: output = weight * v
"""

from engine.subcircuit import SubcircuitDef, ComponentDef, PatchDef
from engine.registry import register_subcircuit


def create_attention_head_def() -> SubcircuitDef:
    """Create and return an AttentionHead subcircuit definition.

    The attention head subcircuit computes single-query attention:
    - Takes 2-element query vector (q0, q1) and 2-element key vector (k0, k1)
    - Computes dot product: score = q0*k0 + q1*k1
    - Passes score through coefficient (weight = 1.0 for now)
    - Multiplies weighted score by value scalar: output = weight * v

    Returns:
        SubcircuitDef: A fully configured attention head subcircuit

    Example:
        >>> attn_def = create_attention_head_def()
        >>> attn_def.name
        'AttentionHead'
        >>> attn_def.inputs
        ['q0', 'q1', 'k0', 'k1', 'v']
        >>> attn_def.outputs
        ['out']
    """
    return SubcircuitDef(
        name="AttentionHead",
        description="Single-query attention: output = (q · k) * v",
        inputs=["q0", "q1", "k0", "k1", "v"],
        outputs=["out"],
        components=[
            # Compute dot product of query and key vectors
            ComponentDef(name="DOT", type="DotProduct", params={"size": 2}),
            # Pass score through coefficient (placeholder for softmax)
            ComponentDef(name="WEIGHT", type="Coefficient", params={"k": 1.0}),
            # Multiply weighted score by value
            ComponentDef(name="MUL", type="Multiplier", params={}),
        ],
        patches=[
            # Query and key to dot product
            PatchDef(source="DOT.out", dest="WEIGHT.in"),
            # Weighted score to multiplier
            PatchDef(source="WEIGHT.out", dest="MUL.x"),
        ],
        input_map={
            "q0": "DOT.a0",
            "q1": "DOT.a1",
            "k0": "DOT.b0",
            "k1": "DOT.b1",
            "v": "MUL.y",
        },
        output_map={
            "out": "MUL.out",
        },
    )


def register_attention_head() -> None:
    """Register the AttentionHead subcircuit with the component registry.

    Adds the AttentionHead subcircuit definition to the registry so it can be
    instantiated using the standard component creation pipeline.

    Example:
        >>> register_attention_head()
        >>> # AttentionHead is now available as a component type
    """
    attention_head_def = create_attention_head_def()
    register_subcircuit("AttentionHead", attention_head_def)
