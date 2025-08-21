"""
MCP 服务器
"""
import asyncio
import websockets
from typing import Any, Dict, Set, Optional
import logging
from .protocol import MCPProtocol, MCPMessage

logger = logging.getLogger(__name__)

class MCPServer:
    """MCP 服务器"""

    def __init__(self, host: str = "localhost", port: int = 8765, enable_heartbeat: bool = False, heartbeat_interval: int = 30):
        self.host = host
        self.port = port
        self.protocol = MCPProtocol()
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self._server: Optional[websockets.server.Serve] = None
        self._hb_task: Optional[asyncio.Task] = None
        self.enable_heartbeat = enable_heartbeat
        self.heartbeat_interval = heartbeat_interval
        self._register_default_handlers()

    def _register_default_handlers(self):
        self.protocol.register_handlers({
            "ping": self._handle_ping,
            "model.info": self._handle_model_info,
            "model.generate": self._handle_model_generate
        })

    async def start(self):
        logger.info("启动 MCP 服务器: %s:%s", self.host, self.port)
        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port
        )
        if self.enable_heartbeat:
            self._hb_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("MCP 服务器已启动")
        # 不自动 Future() 阻塞，让调用方控制生命周期

    async def stop(self):
        if self._hb_task:
            self._hb_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._hb_task
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("MCP 服务器已停止")

    async def _handle_client(self, websocket, path):
        logger.info("客户端连接: %s", websocket.remote_address)
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("客户端断开: %s", websocket.remote_address)
        except Exception as e:
            logger.exception("处理客户端出错: %s", e)
        finally:
            self.clients.discard(websocket)

    async def _process_message(self, websocket, raw_message: str):
        try:
            message_data = self.protocol.deserialize_message(raw_message)
            response = await self.protocol.handle_message(message_data)
            if response:
                await websocket.send(self.protocol.serialize_message(response))
        except Exception as e:
            logger.error("处理消息失败: %s", e)

    async def broadcast(self, method: str, params: Dict[str, Any]):
        if not self.clients:
            return
        notification = self.protocol.create_notification(method, params)
        data = self.protocol.serialize_message(notification)
        coros = []
        for client in list(self.clients):
            coros.append(self._safe_send(client, data))
        await asyncio.gather(*coros, return_exceptions=True)

    async def _safe_send(self, client, data: str):
        try:
            await client.send(data)
        except websockets.exceptions.ConnectionClosed:
            self.clients.discard(client)
        except Exception as e:
            logger.error("广播失败: %s", e)
            self.clients.discard(client)

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            await self.broadcast("heartbeat", {"ts": asyncio.get_running_loop().time()})

    # 默认处理器
    async def _handle_ping(self, params: Dict[str, Any]):
        return {"pong": True, "timestamp": asyncio.get_event_loop().time()}

    async def _handle_model_info(self, params: Dict[str, Any]):
        return {
            "name": "AI Chatbot",
            "version": "1.0.0",
            "capabilities": ["text_generation", "tool_calling", "rag_retrieval"],
            "description": "基于 LangChain 和 LangGraph 的 AI 聊天机器人"
        }

    async def _handle_model_generate(self, params: Dict[str, Any]):
        prompt = params.get("prompt", "")
        response_text = f"AI 回复: 您说的是 '{prompt}'。这是一个示例回复。"
        return {
            "text": response_text,
            "tokens_used": len(response_text.split()),
            "model": "gpt-3.5-turbo"
        }

    def register_handler(self, method: str, handler):
        self.protocol.register_handler(method, handler)