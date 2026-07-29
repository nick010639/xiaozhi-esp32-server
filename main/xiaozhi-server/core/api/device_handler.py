import json
from typing import Any, Dict

from aiohttp import web

from core.api.base_handler import BaseHandler
from plugins_func.register import Action


class DeviceHandler(BaseHandler):
    """供本机 MCP Bridge 调用在线 ESP32 工具的内部接口。"""

    def __init__(self, config: dict, websocket_server):
        super().__init__(config)
        self.websocket_server = websocket_server

        api_config = config.get("internal_device_api", {}) or {}
        self.token = api_config.get("token", "")
        self.allowed_tools = set(api_config.get("allowed_tools", []) or [])

    def _json_response(
        self,
        data: Dict[str, Any],
        status: int = 200,
    ) -> web.Response:
        return web.Response(
            text=json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            content_type="application/json",
            status=status,
        )

    def _verify_token(self, request: web.Request) -> bool:
        auth_header = request.headers.get("Authorization", "")
        if not self.token or not auth_header.startswith("Bearer "):
            return False

        return auth_header[7:] == self.token

    async def handle_post(self, request: web.Request) -> web.Response:
        if not self._verify_token(request):
            return self._json_response(
                {"success": False, "error": "未授权"},
                status=401,
            )

        try:
            body = await request.json()
        except Exception:
            return self._json_response(
                {"success": False, "error": "请求体必须是 JSON"},
                status=400,
            )

        device_id = body.get("device_id", "")
        tool_name = body.get("tool_name", "")
        arguments = body.get("arguments", {})

        if not device_id or not tool_name:
            return self._json_response(
                {
                    "success": False,
                    "error": "缺少 device_id 或 tool_name",
                },
                status=400,
            )

        if not isinstance(arguments, dict):
            return self._json_response(
                {"success": False, "error": "arguments 必须是对象"},
                status=400,
            )

        if tool_name not in self.allowed_tools:
            return self._json_response(
                {"success": False, "error": f"工具 {tool_name} 不在白名单中"},
                status=403,
            )

        connection = self.websocket_server.get_connection(device_id)
        if connection is None:
            return self._json_response(
                {"success": False, "error": "设备当前不在线"},
                status=404,
            )

        if not connection.func_handler:
            return self._json_response(
                {"success": False, "error": "设备工具处理器尚未初始化"},
                status=409,
            )

        result = await connection.func_handler.tool_manager.execute_tool(
            tool_name,
            arguments,
        )

        success = result.action not in {
            Action.ERROR,
            Action.NOTFOUND,
        }

        return self._json_response(
            {
                "success": success,
                "action": result.action.name,
                "action_code": result.action.code,
                "result": result.result,
                "response": result.response,
            },
            status=200 if success else 400,
        )
