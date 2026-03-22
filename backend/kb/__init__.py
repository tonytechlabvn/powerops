"""Knowledge Base — interactive Terraform curriculum with quizzes and labs.

Public surface:
    from backend.kb import CurriculumLoader, QuizEngine, LabValidator, ProgressTracker
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_KB_DIR = Path(__file__).parent


def _load_kebab(filename: str, alias: str):
    """Load a kebab-case sibling module via importlib."""
    full = f"backend.kb.{alias}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, _KB_DIR / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate {filename} at {_KB_DIR}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_cl = _load_kebab("curriculum-loader.py", "curriculum_loader")
_qe = _load_kebab("quiz-engine.py", "quiz_engine")
_lv = _load_kebab("lab-validator.py", "lab_validator")
_pt = _load_kebab("progress-tracker.py", "progress_tracker")

CurriculumLoader = _cl.CurriculumLoader
QuizEngine = _qe.QuizEngine
LabValidator = _lv.LabValidator
ProgressTracker = _pt.ProgressTracker

__all__ = ["CurriculumLoader", "QuizEngine", "LabValidator", "ProgressTracker"]
