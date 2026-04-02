"""
Tests for core exceptions.
"""

import pytest
from crawlforge.core.exceptions import (
    CrawlForgeError, AdapterError, DetectionError,
    ExecutionError, TemplateMatchError, EvolutionError,
    RuntimeError as CFRuntimeError, ConfigurationError,
)


def test_crawlforge_error_base():
    with pytest.raises(CrawlForgeError):
        raise CrawlForgeError("test")

def test_adapter_error():
    with pytest.raises(AdapterError, match="test"):
        raise AdapterError("test")

def test_detection_error():
    with pytest.raises(DetectionError):
        raise DetectionError("detection failed")

def test_execution_error():
    with pytest.raises(ExecutionError):
        raise ExecutionError("execution failed")

def test_template_match_error():
    with pytest.raises(TemplateMatchError):
        raise TemplateMatchError("template not found")

def test_evolution_error():
    with pytest.raises(EvolutionError):
        raise EvolutionError("evolution failed")

def test_runtime_error():
    with pytest.raises(CFRuntimeError):
        raise CFRuntimeError("runtime error")

def test_configuration_error():
    with pytest.raises(ConfigurationError):
        raise ConfigurationError("config error")

def test_error_hierarchy():
    """All errors should inherit from CrawlForgeError."""
    assert issubclass(AdapterError, CrawlForgeError)
    assert issubclass(DetectionError, AdapterError)
    assert issubclass(ExecutionError, CrawlForgeError)
    assert issubclass(TemplateMatchError, CrawlForgeError)
    assert issubclass(EvolutionError, CrawlForgeError)
    assert issubclass(CFRuntimeError, CrawlForgeError)
    assert issubclass(ConfigurationError, CrawlForgeError)
