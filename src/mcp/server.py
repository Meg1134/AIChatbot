"""
MCP 服务器
"""
import asyncio
import websockets
from typing import Any, Dict, Set
from .protocol import MCPProtocol, MCPMessage


class MCPServer:
    """MCP 服务器"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """初始化服务器"""
        self.host = host
        self.port = port
        self.protocol = MCPProtocol()
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.protocol.register_handler("ping", self._handle_ping)
        self.protocol.register_handler("model.info", self._handle_model_info)
        self.protocol.register_handler("model.generate", self._handle_model_generate)
    
    async def start(self):
        """启动服务器"""
        print(f"启动 MCP 服务器在 {self.host}:{self.port}")
        
        async with websockets.serve(
            self._handle_client,
            self.host,
            self.port
        ):
            print("MCP 服务器已启动，等待连接...")
            await asyncio.Future()  # 永远运行
    
    async def _handle_client(self, websocket, path):
        """处理客户端连接"""
        print(f"新客户端连接: {websocket.remote_address}")
        self.clients.add(websocket)
        
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"客户端断开连接: {websocket.remote_address}")
        except Exception as e:
            print(f"处理客户端时出错: {e}")
        finally:
            self.clients.discard(websocket)
    
    async def _process_message(self, websocket, raw_message: str):
        """处理客户端消息"""
        try:
            message_data = self.protocol.deserialize_message(raw_message)
            response = await self.protocol.handle_message(message_data)
            
            if response:
                response_data = self.protocol.serialize_message(response)
                await websocket.send(response_data)
                
        except Exception as e:
            print(f"处理消息时出错: {e}")
    
    async def broadcast(self, method: str, params: Dict[str, Any]):
        """广播通知给所有客户端"""
        if not self.clients:
            return
        
        notification = self.protocol.create_notification(method, params)
        message_data = self.protocol.serialize_message(notification)
        
        # 发送给所有连接的客户端
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await client.send(message_data)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                print(f"发送广播消息时出错: {e}")
                disconnected_clients.add(client)
        
        # 清理断开的连接
        for client in disconnected_clients:
            self.clients.discard(client)
    
    # 默认处理器
    async def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 ping 请求"""
        return {"pong": True, "timestamp": asyncio.get_event_loop().time()}
    
    async def _handle_model_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理模型信息请求"""
        return {
            "name": "AI Chatbot",
            "version": "1.0.0",
            "capabilities": [
                "text_generation",
                "tool_calling",
                "rag_retrieval"
            ],
            "description": "基于 LangChain 和 LangGraph 的 AI 聊天机器人"
        }
    
    async def _handle_model_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理文本生成请求"""
        prompt = params.get("prompt", "")
        
        # 这里应该调用实际的模型生成逻辑
        # 现在返回一个模拟响应
        response_text = f"AI 回复: 您说的是 '{prompt}'。这是一个示例回复。"
        
        return {
            "text": response_text,
            "tokens_used": len(response_text.split()),
            "model": "gpt-3.5-turbo"
        }
    
    def register_handler(self, method: str, handler):
        """注册自定义处理器"""
        self.protocol.register_handler(method, handler)
