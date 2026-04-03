"""
AI Pipeline configuration.

Supports environment variable overrides:
- NEWAPI_URL
- NEWAPI_KEY
- VISION_MODEL
- CHAT_MODEL
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- OLLAMA_URL
"""

import os
from dataclasses import dataclass


@dataclass
class AIPipelineConfig:
    """Configuration for AI Pipeline with newapi backend."""

    # newapi 统一入口 (env: NEWAPI_URL)
    newapi_url: str = ""

    # newapi key (env: NEWAPI_KEY)
    newapi_key: str = ""

    # 模型配置 (env: VISION_MODEL, CHAT_MODEL)
    vision_model: str = ""
    chat_model: str = ""

    # 其他后端（备用）(env: OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_URL)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_url: str = ""

    # Pipeline 设置
    max_retries: int = 3
    sandbox_enabled: bool = True
    confidence_threshold: float = 0.7

    def __post_init__(self):
        """Apply environment variable overrides."""
        # newapi
        if os.environ.get("NEWAPI_URL"):
            self.newapi_url = os.environ["NEWAPI_URL"]
        elif not self.newapi_url:
            self.newapi_url = "http://localhost:5337/v1"

        if os.environ.get("NEWAPI_KEY"):
            self.newapi_key = os.environ["NEWAPI_KEY"]
        elif not self.newapi_key:
            self.newapi_key = ""

        # Model names
        if os.environ.get("VISION_MODEL"):
            self.vision_model = os.environ["VISION_MODEL"]
        elif not self.vision_model:
            self.vision_model = "MiniMax-M2.7"

        if os.environ.get("CHAT_MODEL"):
            self.chat_model = os.environ["CHAT_MODEL"]
        elif not self.chat_model:
            self.chat_model = "MiniMax-M2.5-highspeed"

        # Other backends
        if os.environ.get("OPENAI_API_KEY"):
            self.openai_api_key = os.environ["OPENAI_API_KEY"]

        if os.environ.get("ANTHROPIC_API_KEY"):
            self.anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]

        if os.environ.get("OLLAMA_URL"):
            self.ollama_url = os.environ["OLLAMA_URL"]
        elif not self.ollama_url:
            self.ollama_url = "http://localhost:11434"
