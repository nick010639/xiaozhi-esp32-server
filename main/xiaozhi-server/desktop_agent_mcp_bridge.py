import json
import os
from pathlib import Path
from typing import Any

import httpx
import yaml
from mcp.server.fastmcp import FastMCP


CONFIG_PATH = Path(
    os.getenv(
        "DESKTOP_AGENT_CONFIG_PATH",
        "/opt/xiaozhi-esp32-server/data/.config.yaml",
    )
)
DEVICE_ID_ENV = "DESKTOP_AGENT_DEVICE_ID"

mcp = FastMCP(
    name="Desktop Agent MCP Bridge",
    instructions="通过 xiaozhi-server 安全调用在线桌面智能体设备能力。",
)


def _load_internal_api_config() -> tuple[str, str]:
    if not CONFIG_PATH.is_file():
        raise RuntimeError(f"找不到私有配置文件：{CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}

    api_config = config.get("internal_device_api", {}) or {}
    if not api_config.get("enabled", False):
        raise RuntimeError("内部设备调用接口尚未启用")

    token = api_config.get("token", "")
    if not token:
        raise RuntimeError("内部设备调用接口没有配置 Token")

    host = api_config.get("host", "127.0.0.1")
    port = int(api_config.get("port", 8004))
    base_url = f"http://{host}:{port}"

    return base_url, token


def _get_device_id() -> str:
    device_id = os.getenv(DEVICE_ID_ENV, "").strip()
    if not device_id:
        raise RuntimeError(f"缺少环境变量 {DEVICE_ID_ENV}")

    return device_id


@mcp.tool()
async def get_device_status() -> dict[str, Any]:
    """读取当前桌面智能体的音量、屏幕和网络状态。"""
    base_url, token = _load_internal_api_config()
    device_id = _get_device_id()

    payload = {
        "device_id": device_id,
        "tool_name": "self_get_device_status",
        "arguments": {},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{base_url}/internal/device/call",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    try:
        response_data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"内部设备接口返回了无效 JSON，HTTP {response.status_code}"
        ) from exc

    if response.status_code != 200 or not response_data.get("success"):
        error = response_data.get("error", "设备调用失败")
        raise RuntimeError(f"{error}，HTTP {response.status_code}")

    result = response_data.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            pass

    return {
        "device_id": device_id,
        "status": result,
        "action": response_data.get("action"),
    }


@mcp.tool()
async def set_volume(volume: int) -> dict[str, Any]:
    """将当前桌面智能体的扬声器音量设置为 0 到 100。"""
    if isinstance(volume, bool) or not isinstance(volume, int):
        raise ValueError("volume 必须是 0 到 100 的整数")

    if not 0 <= volume <= 100:
        raise ValueError("volume 必须在 0 到 100 之间")

    base_url, token = _load_internal_api_config()
    device_id = _get_device_id()

    payload = {
        "device_id": device_id,
        "tool_name": "self_audio_speaker_set_volume",
        "arguments": {"volume": volume},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{base_url}/internal/device/call",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    try:
        response_data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"内部设备接口返回了无效 JSON，HTTP {response.status_code}"
        ) from exc

    if response.status_code != 200 or not response_data.get("success"):
        error = response_data.get("error", "设备音量设置失败")
        raise RuntimeError(f"{error}，HTTP {response.status_code}")

    return {
        "device_id": device_id,
        "volume": volume,
        "result": response_data.get("result"),
        "action": response_data.get("action"),
    }

@mcp.tool()
async def set_brightness(brightness: int) -> dict[str, Any]:
    """Set screen brightness from 60 to 100 for this hardware."""
    if isinstance(brightness, bool) or not isinstance(brightness, int):
        raise ValueError("brightness must be an integer from 60 to 100")

    if not 60 <= brightness <= 100:
        raise ValueError("brightness must be between 60 and 100")

    base_url, token = _load_internal_api_config()
    device_id = _get_device_id()

    payload = {
        "device_id": device_id,
        "tool_name": "self_screen_set_brightness",
        "arguments": {"brightness": brightness},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{base_url}/internal/device/call",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    try:
        response_data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Internal device API returned invalid JSON, HTTP {response.status_code}"
        ) from exc

    if response.status_code != 200 or not response_data.get("success"):
        error = response_data.get("error", "Failed to set screen brightness")
        raise RuntimeError(f"{error}, HTTP {response.status_code}")

    return {
        "device_id": device_id,
        "brightness": brightness,
        "result": response_data.get("result"),
        "action": response_data.get("action"),
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")
