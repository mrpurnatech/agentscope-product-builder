"""
DEPRECATED: Gateway has been replaced by:
  - core/models.py     — model factory (create_fast_model, create_default_model, create_smart_model)
  - core/cost_tracker.py — cost tracking singleton

This file is kept for backward compatibility. The CostTracker is the new way.
"""
from core.cost_tracker import cost_tracker

# Backward-compatible alias
gateway = cost_tracker
