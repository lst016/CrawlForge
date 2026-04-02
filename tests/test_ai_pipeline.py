"""
Tests for AIRouter stub.
"""

import pytest
from crawlforge.ai_pipeline.pipeline import AIRouter


@pytest.mark.asyncio
async def test_airouter_stub_vision():
    router = AIRouter()
    result = await router.vision_analyze(b"fake_image", "test prompt")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_airouter_stub_llm():
    router = AIRouter()
    result = await router.llm_generate("test prompt")
    assert isinstance(result, str)
    assert len(result) > 0


def test_airouter_stub_vision_output():
    result = AIRouter._stub_vision_output("test")
    assert "Vision analysis" in result


def test_airouter_stub_llm_output():
    result = AIRouter._stub_llm_output("test")
    assert "Action plan" in result
