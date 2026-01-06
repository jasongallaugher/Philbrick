"""Subcircuit definitions (macros) for reusable circuit blocks."""

from engine.subcircuits.softmax import create_softmax_def, register_softmax
from engine.subcircuits.attention import create_attention_head_def, register_attention_head

__all__ = [
    "create_softmax_def",
    "register_softmax",
    "create_attention_head_def",
    "register_attention_head",
]
