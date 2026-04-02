"""
AdapterRegistry - 适配器注册中心

管理所有游戏适配器的注册、发现和加载。
"""

from typing import Dict, Optional, Type
import json
from pathlib import Path
import hashlib


class AdapterRegistry:
    """适配器注册中心"""

    _instance: Optional["AdapterRegistry"] = None
    _adapters: Dict[str, dict] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._adapters = {}
        return cls._instance

    def register(
        self,
        game_name: str,
        adapter_class: Type,
        version: str = "1.0.0",
        metadata: dict = None,
    ) -> None:
        """
        注册游戏适配器

        Args:
            game_name: 游戏名称
            adapter_class: 适配器类
            version: 版本号
            metadata: 元数据（描述、作者等）
        """
        key = self._make_key(game_name)
        self._adapters[key] = {
            "class": adapter_class,
            "version": version,
            "game_name": game_name,
            "metadata": metadata or {},
        }

    def get(self, game_name: str) -> Optional[dict]:
        """获取适配器信息"""
        key = self._make_key(game_name)
        return self._adapters.get(key)

    def list_all(self) -> Dict[str, dict]:
        """列出所有已注册的适配器"""
        return self._adapters.copy()

    def unregister(self, game_name: str) -> bool:
        """注销适配器"""
        key = self._make_key(game_name)
        if key in self._adapters:
            del self._adapters[key]
            return True
        return False

    @staticmethod
    def _make_key(game_name: str) -> str:
        """生成唯一键"""
        return hashlib.md5(game_name.lower().encode()).hexdigest()[:12]

    def save_to_file(self, path: Path) -> None:
        """保存注册表到文件"""
        data = {
            k: {
                "version": v["version"],
                "game_name": v["game_name"],
                "metadata": v["metadata"],
            }
            for k, v in self._adapters.items()
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, path: Path) -> None:
        """从文件加载注册表"""
        if not path.exists():
            return
        with open(path) as f:
            data = json.load(f)
        # 注意：class 需要重新导入，不存储
