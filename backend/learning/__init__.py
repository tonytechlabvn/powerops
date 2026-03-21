"""TerraBot learning engine — glossary, explainer, and tutorials.

Public surface:
    from backend.learning.glossary import CONCEPTS, get_concept, list_concepts, search_concepts
    from backend.learning.explainer import Explainer
    from backend.learning.tutorials import TutorialEngine, TutorialSession
"""
from backend.learning.glossary import CONCEPTS, get_concept, list_concepts, search_concepts
from backend.learning.explainer import Explainer
from backend.learning.tutorials import TutorialEngine, TutorialSession

__all__ = [
    "CONCEPTS",
    "get_concept",
    "list_concepts",
    "search_concepts",
    "Explainer",
    "TutorialEngine",
    "TutorialSession",
]
