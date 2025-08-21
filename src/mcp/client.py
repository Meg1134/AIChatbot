"""
MCP 客户端
"""
import asyncio
import websockets
from typing import Any, Dict, Optional
import logging
from .protocol import MCPProtocol, MCPMessage

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP 客户端"""

    def __init__(self, server_url: str, auto_reconnect: bool = False, reconnect_interval: int = 5):
        self.server_url = server_url
        self.protocol = MCPProtocol()
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self._recv_task: Optional[asyncio.Task] = None
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self._closing = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    async def connect(self):
        if self.websocket and not self.websocket.closed:
            return
        try:
            self.websocket = await websockets.connect(self.server_url)
            logger.info("已连接 MCP 服务器: %s", self.server_url)
            self._recv_task = asyncio.create_task(self._message_loop())
        except Exception as e:
            logger.error("连接失败: %s", e)
            raise

    async def disconnect(self):
        self._closing = True
        if self.websocket:
            await self.websocket.close()
        if self._recv_task:
            self._recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._recv_task
        # 取消未完成请求
        for fut in self.pending_requests.values():
            if not fut.done():
                fut.set_exception(ConnectionError("连接已关闭"))
        self.pending_requests.clear()
        logger.info("已断开 MCP 服务器连接")

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Any:
        if not self.websocket or self.websocket.closed:
            raise ConnectionError("未连接到服务器")
        request = self.protocol.create_request(method, params)
        fut = asyncio.get_event_loop().create_future()
        self.pending_requests[request.id] = fut
        try:
            await self.websocket.send(self.protocol.serialize_message(request))
            return await asyncio.wait_for(fut, timeout=timeout)
        except Exception:
            self.pending_requests.pop(request.id, None)
            raise

    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        if not self.websocket or self.websocket.closed:
            raise ConnectionError("未连接到服务器")
        notification = self.protocol.create_notification(method, params)
        await self.websocket.send(self.protocol.serialize_message(notification))

    async def _message_loop(self):
        try:
            async for raw in self.websocket:
                await self._handle_message(raw)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("服务器关闭连接")
            await self._on_disconnect()
        except Exception as e:
            logger.error("消息循环异常: %s", e)
            await self._on_disconnect()

    async def _on_disconnect(self):
        if self._closing:
            return
        # 拒绝所有挂起请求
        for fut in self.pending_requests.values():
            if not fut.done():
                fut.set_exception(ConnectionError("连接丢失"))
        self.pending_requests.clear()
        if self.auto_reconnect:
            await asyncio.sleep(self.reconnect_interval)
            try:
                await self.connect()
            except Exception:
                logger.error("重连失败，稍后再试")
                asyncio.create_task(self._delayed_reconnect())

    async def _delayed_reconnect(self):
        await asyncio.sleep(self.reconnect_interval)
        try:
            await self.connect()
        except Exception:
            asyncio.create_task(self._delayed_reconnect())

    async def _handle_message(self, raw: str):
        try:
            data = self.protocol.deserialize_message(raw)
            msg = MCPMessage(**data)
            if msg.type in ("response", "error") and msg.id:
                fut = self.pending_requests.pop(msg.id, None)
                if fut and not fut.done():
                    if msg.type == "response":
                        fut.set_result(msg.result)
                    else:
                        fut.set_exception(Exception(msg.error.get("message", "Unknown error")))
            elif msg.type == "notification":
                await self._handle_notification(msg)
        except Exception as e:
            logger.error("处理消息失败: %s", e)

    async def _handle_notification(self, message: MCPMessage):
        logger.info("收到通知: %s %s", message.method, message.params)

    async def get_model_info(self):
        return await self.send_request("model.info")

    async def generate_text(self, prompt: str, **kwargs):
        params = {"prompt": prompt, **kwargs}
        result = await self.send_request("model.generate", params)
        return result.get("text", "")