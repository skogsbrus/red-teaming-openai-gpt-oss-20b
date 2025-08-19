"""
Adaptive Feedback Strategy Module

This module implements a feedback loop between red team and blue team models
to iteratively refine prompts for detecting unsafe behaviors.
"""

from .adaptive_feedback import AdaptiveFeedbackStrategy, AdaptiveFeedbackConfig

__all__ = [
    "AdaptiveFeedbackStrategy",
    "AdaptiveFeedbackConfig"
]

__version__ = "1.0.0"
