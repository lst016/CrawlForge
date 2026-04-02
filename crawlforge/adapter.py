"""
GameAdapter - 游戏适配器基类

所有游戏适配器都必须继承此基类，实现标准化接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
import base64
from pathlib import Path


class RuntimeType(Enum):
    """支持的运行时类型"""
    PLAYWRIGHT = "playwright"      # 页游/H5
    ADB = "adb"                   # 手游
    WIN32 = "win32"              # PC游戏
    HTTP = "http"                # API游戏


@dataclass
class GameState:
    """游戏状态"""
    screen: Optional[bytes] = None           # 截图原始数据
    screen_b64: Optional[str] = None          # Base64 编码的截图
    ui_elements: list[dict] = field(default_factory=list)  # 识别的UI元素
    game_phase: str = "unknown"               # 游戏阶段
    gold_amount: Optional[int] = None          # 货币数量
    player_level: Optional[int] = None        # 玩家等级
    raw_data: dict = field(default_factory=dict)  # 原始数据


@dataclass
class Action:
    """游戏操作"""
    action_type: str                          # tap / swipe / input / wait
    x: Optional[int] = None                   # 点击X坐标
    y: Optional[int] = None                   # 点击Y坐标
    x1: Optional[int] = None                  # 滑动起点X
    y1: Optional[int] = None                 # 滑动起点Y
    x2: Optional[int] = None                 # 滑动终点X
    y2: Optional[int] = None                 # 滑动终点Y
    text: Optional[str] = None               # 输入文本
    duration_ms: int = 300                   # 持续时间


@dataclass
class GameData:
    """游戏数据（爬取结果）"""
    game_name: str
    game_version: str = "unknown"
    data_type: str                           # gold / characters / items / etc.
    value: Any                               # 具体数据
    timestamp: float = 0                    # 采集时间戳
    raw: dict = field(default_factory=dict) # 原始数据


class GameAdapter(ABC):
    """
    游戏适配器基类

    所有游戏适配器必须实现以下方法：
    1. detect_state - 检测当前游戏状态
    2. generate_action - AI 生成下一步操作
    3. extract_data - 提取游戏数据
    4. evolve - AI 自动修复/优化
    """

    def __init__(self, runtime: "Runtime"):
        self.runtime = runtime
        self.game_name: str = "unknown"
        self.game_version: str = "unknown"
        self.runtime_type: RuntimeType = RuntimeType.PLAYWRIGHT
        self._screen_cache: Optional[bytes] = None
        self._last_state: Optional[GameState] = None

    @abstractmethod
    async def detect_state(self, screenshot: bytes) -> GameState:
        """
        检测当前游戏状态

        Args:
            screenshot: 游戏截图原始数据

        Returns:
            GameState: 解析后的游戏状态
        """
        ...

    @abstractmethod
    async def generate_action(self, state: GameState, goal: str) -> Action:
        """
        AI 根据当前状态和目标生成下一步操作

        Args:
            state: 当前游戏状态
            goal: 操作目标，如 "点击开始战斗"、"领取奖励"

        Returns:
            Action: 要执行的操作
        """
        ...

    @abstractmethod
    async def extract_data(self, state: GameState) -> GameData:
        """
        从游戏状态中提取数据

        Args:
            state: 游戏状态

        Returns:
            GameData: 提取的游戏数据
        """
        ...

    async def evolve(self, error_feedback: str) -> bool:
        """
        AI 根据错误反馈自动修复适配器

        Args:
            error_feedback: 错误描述

        Returns:
            bool: 是否修复成功
        """
        # 默认实现由 AI Generator 完成
        from .generator import AIGenerator
        generator = AIGenerator()
        return await generator.fix_adapter(self, error_feedback)

    async def screenshot(self) -> bytes:
        """截取当前游戏画面"""
        screen = await self.runtime.screenshot()
        self._screen_cache = screen
        return screen

    async def execute_action(self, action: Action) -> None:
        """执行游戏操作"""
        await self.runtime.execute(action)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} game={self.game_name}>"
