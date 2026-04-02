"""
Runtime - 多运行时抽象

封装不同游戏类型的运行时环境。
"""

from abc import ABC, abstractmethod
from typing import Optional
import asyncio
from .adapter import Action


class Runtime(ABC):
    """运行时基类"""

    @abstractmethod
    async def screenshot(self) -> bytes:
        """截取屏幕画面"""
        ...

    @abstractmethod
    async def execute(self, action: Action) -> None:
        """执行操作"""
        ...

    @abstractmethod
    async def start(self) -> None:
        """启动运行时"""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """停止运行时"""
        ...

    @abstractmethod
    def is_alive(self) -> bool:
        """检查运行时是否存活"""
        ...
