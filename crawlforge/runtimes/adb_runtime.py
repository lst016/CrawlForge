"""
ADB Runtime - 手游 Android 运行时

通过 ADB 控制安卓模拟器或真机。
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from .runtime import Runtime
from .adapter import Action


class ADBRuntime(Runtime):
    """ADB 安卓运行时"""

    def __init__(self, device_id: Optional[str] = None):
        """
        Args:
            device_id: ADB 设备 ID，None 则使用第一个设备
        """
        self.device_id = device_id
        self._adb_path = "adb"  # 假设 adb 在 PATH 中

    async def screenshot(self) -> bytes:
        """截图"""
        cmd = self._build_cmd(["exec-out", "screencap", "-p"])
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await result.communicate()
        return stdout

    async def execute(self, action: Action) -> None:
        """执行操作"""
        cmd = self._build_cmd(self._action_to_adb(action))
        await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def start(self) -> None:
        """启动 ADB 服务"""
        cmd = [self._adb_path, "start-server"]
        await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def stop(self) -> None:
        """停止 ADB 服务"""
        # 不停止全局 ADB 服务

    def is_alive(self) -> bool:
        """检查设备是否连接"""
        try:
            result = subprocess.run(
                self._build_cmd(["get-state"]),
                capture_output=True,
                timeout=5,
            )
            return b"device" in result.stdout
        except:
            return False

    def _build_cmd(self, args: list[str]) -> list[str]:
        """构建 ADB 命令"""
        cmd = [self._adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    @staticmethod
    def _action_to_adb(action: Action) -> list[str]:
        """将 Action 转换为 ADB 命令"""
        if action.action_type == "tap":
            return ["shell", "input", "tap", str(action.x), str(action.y)]
        elif action.action_type == "swipe":
            return [
                "shell", "input", "swipe",
                str(action.x1), str(action.y1),
                str(action.x2), str(action.y2),
            ]
        elif action.action_type == "text":
            return ["shell", "input", "text", action.text.replace(" ", "%s")]
        elif action.action_type == "wait":
            return ["shell", "sleep", str(action.duration_ms / 1000)]
        return []

    async def install_apk(self, apk_path: Path) -> bool:
        """安装 APK"""
        cmd = self._build_cmd(["install", "-r", str(apk_path)])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return b"Success" in stdout

    async def list_packages(self) -> list[str]:
        """列出已安装的应用"""
        cmd = self._build_cmd(["shell", "pm", "list", "packages"])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return [
            line.replace("package:", "").strip()
            for line in stdout.decode().split("\n")
            if line.startswith("package:")
        ]
