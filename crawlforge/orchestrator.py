"""
CrawlForge - AI 任务编排器

主要入口类，协调所有模块工作。
"""

import asyncio
from typing import Optional, Type
from pathlib import Path
import json

from .adapter import GameAdapter, GameState, Action, GameData, RuntimeType
from .runtime import Runtime
from .registry import AdapterRegistry
from .generator import AIGenerator


class CrawlForge:
    """
    CrawlForge 主类

    使用示例：
    ```python
    from crawlforge import CrawlForge

    cf = CrawlForge()
    adapter = await cf.generate_adapter("原神")
    data = await adapter.extract(gold_info)
    ```
    """

    def __init__(
        self,
        registry_path: Optional[Path] = None,
        ai_model: str = "claude",
    ):
        self.registry = AdapterRegistry()
        self.generator = AIGenerator(model=ai_model)
        self._runtime: Optional[Runtime] = None
        self._active_adapters: dict[str, GameAdapter] = {}

        # 加载已注册的适配器
        if registry_path and registry_path.exists():
            self.registry.load_from_file(registry_path)

    async def generate_adapter(
        self,
        game_name: str,
        screenshot: bytes,
        game_type: str = "gacha",
        runtime: Optional[Runtime] = None,
    ) -> GameAdapter:
        """
        AI 分析游戏并生成适配器

        Args:
            game_name: 游戏名称
            screenshot: 游戏截图
            game_type: 游戏类型
            runtime: 可选的运行时实例

        Returns:
            GameAdapter: 生成的适配器实例
        """
        # AI 生成代码
        code = await self.generator.generate_adapter(
            game_name, screenshot, game_type
        )

        # TODO: 动态编译代码生成适配器实例
        # 暂时返回占位符
        print(f"Generated code for {game_name}:")
        print(code[:200], "...")

        raise NotImplementedError("Dynamic code loading not yet implemented")

    async def register_existing_adapter(
        self,
        adapter_class: Type[GameAdapter],
        game_name: str,
        version: str = "1.0.0",
        metadata: dict = None,
    ) -> None:
        """
        注册已有的适配器类

        Args:
            adapter_class: 适配器类
            game_name: 游戏名称
            version: 版本号
            metadata: 元数据
        """
        self.registry.register(
            game_name=game_name,
            adapter_class=adapter_class,
            version=version,
            metadata=metadata,
        )

    async def list_adapters(self) -> dict:
        """列出所有已注册的适配器"""
        return self.registry.list_all()

    def set_runtime(self, runtime: Runtime) -> None:
        """设置默认运行时"""
        self._runtime = runtime

    async def close(self) -> None:
        """关闭并清理资源"""
        if self._runtime:
            await self._runtime.stop()
        self._active_adapters.clear()
