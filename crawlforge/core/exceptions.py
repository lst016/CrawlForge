"""
Core exceptions for CrawlForge.
"""

class CrawlForgeError(Exception):
    """Base exception for all CrawlForge errors."""
    pass


class AdapterError(CrawlForgeError):
    """Adapter-related errors."""
    pass


class DetectionError(AdapterError):
    """Failed to detect game state."""
    pass


class ExecutionError(CrawlForgeError):
    """Action execution failed."""
    pass


class TemplateMatchError(CrawlForgeError):
    """Template matching failed."""
    pass


class EvolutionError(CrawlForgeError):
    """Adapter evolution failed."""
    pass


class RuntimeError(CrawlForgeError):
    """Runtime-related errors."""
    pass


class ConfigurationError(CrawlForgeError):
    """Configuration errors."""
    pass
