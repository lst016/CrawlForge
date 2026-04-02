"""
Template Store - screenshot template management and matching.
"""

from .store import TemplateStore, Template, MatchResult
from .matcher import TemplateMatcher

__all__ = ["TemplateStore", "Template", "MatchResult", "TemplateMatcher"]
