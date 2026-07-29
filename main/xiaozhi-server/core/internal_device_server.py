import asyncio

from aiohttp import web

from config.logger import setup_logging
from core.api.device_handler import DeviceHandler

TAG = __name__


class InternalDeviceApiServer:
    """仅供本机 Desktop Agent MCP Bridge 使用的设备调用服务。"""

    def __init__(self, config: dict, websocket_server):
        self.config = config
        self.websocket_server = websocket_server
        self.logger = setup_logging(config)

        api_config = config.get("internal_device_api", {}) or {}
        self.enabled = api_config.get("enabled", False)
        self.host = api_config.get("host", "127.0.0.1")
        self.port = int(api_config.get("port", 8004))
        self.token = api_config.get("token", "")

        self.device_handler = DeviceHandler(config, websocket_server)

    async def start(self):
        if not self.enabled:
            self.logger.bind(tag=TAG).info("内部设备调用接口未启用")
            return

        if self.host not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError("内部设备调用接口只允许绑定本机回环地址")

        if not self.token:
            raise RuntimeError("内部设备调用接口已启用，但没有配置 token")

        app = web.Application(client_max_size=64 * 1024)
        app.add_routes(
            [
                web.post(
                    "/internal/device/call",
                    self.device_handler.handle_post,
                ),
            ]
        )

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        self.logger.bind(tag=TAG).info(
            f"内部设备调用接口已启动: http://{self.host}:{self.port}"
        )

        while True:
            await asyncio.sleep(3600)
