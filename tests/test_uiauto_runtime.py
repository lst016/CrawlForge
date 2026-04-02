"""
Tests for UIAutoRuntime.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from crawlforge.uiauto.uiauto_runtime import UIAutoRuntime


class TestUIAutoRuntime:
    @pytest.fixture
    def runtime(self):
        return UIAutoRuntime(device_id="test_device")

    def test_init(self, runtime):
        assert runtime.device_id == "test_device"
        assert runtime._u2_device is None

    def test_init_no_device(self):
        runtime = UIAutoRuntime()
        assert runtime.device_id is None

    def test_build_adb_cmd(self, runtime):
        cmd = runtime._build_adb_cmd(["shell", "input", "tap", "100", "200"])
        assert cmd == ["adb", "-s", "test_device", "shell", "input", "tap", "100", "200"]

    def test_build_adb_cmd_no_device(self):
        runtime = UIAutoRuntime()
        cmd = runtime._build_adb_cmd(["shell", "input", "tap"])
        assert cmd == ["adb", "shell", "input", "tap"]

    @pytest.mark.asyncio
    async def test_screenshot(self, runtime):
        mock_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with patch.object(
            runtime,
            "_build_adb_cmd",
            return_value=["adb", "-s", "test_device", "exec-out", "screencap", "-p"],
        ):
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.communicate = AsyncMock(return_value=(mock_bytes, b""))
                mock_exec.return_value = mock_proc

                result = await runtime.screenshot()
                assert result == mock_bytes

    @pytest.mark.asyncio
    async def test_tap(self, runtime):
        mock_device = MagicMock()
        runtime._u2_device = mock_device

        await runtime.tap(100, 200)
        mock_device.click.assert_called_once_with(100, 200)

    @pytest.mark.asyncio
    async def test_swipe(self, runtime):
        mock_device = MagicMock()
        runtime._u2_device = mock_device

        await runtime.swipe(100, 200, 300, 400, duration_ms=500)
        mock_device.swipe.assert_called_once_with(100, 200, 300, 400, 0.5)

    @pytest.mark.asyncio
    async def test_press_back(self, runtime):
        with patch.object(
            runtime, "_build_adb_cmd", return_value=["adb", "shell", "input", "keyevent", "KEYCODE_BACK"]
        ):
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.wait = AsyncMock()
                mock_exec.return_value = mock_proc

                await runtime.press_back()
                mock_exec.assert_called_once()

    def test_is_alive_true(self, runtime):
        with patch.object(runtime, "_build_adb_cmd", return_value=["adb", "get-state"]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout=b"device\n")
                assert runtime.is_alive() is True

    def test_is_alive_false(self, runtime):
        with patch.object(runtime, "_build_adb_cmd", return_value=["adb", "get-state"]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout=b"offline\n")
                assert runtime.is_alive() is False

    def test_is_alive_exception(self, runtime):
        with patch.object(runtime, "_build_adb_cmd", return_value=["adb"]):
            with patch("subprocess.run", side_effect=Exception("ADB error")):
                assert runtime.is_alive() is False
