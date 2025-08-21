"""
MCP 客户端
"""
import asyncio
import websockets
from typing import Any, Dict, Optional
from .protocol import MCPProtocol, MCPMessage


class MCPClient:
    """MCP 客户端"""
    
    def __init__(self, server_url: str):
        """初始化客户端"""
        self.server_url = server_url
        self.protocol = MCPProtocol()
        self.websocket = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
    
    async def connect(self):
        """连接到服务器"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"已连接到 MCP 服务器: {self.server_url}")
            
            # 启动消息处理循环
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            print(f"连接到服务器失败: {e}")
            raise
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            print("已断开与 MCP 服务器的连接")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, 
                          timeout: float = 30.0) -> Any:
        """发送请求并等待响应"""
        if not self.websocket:
            raise ConnectionError("未连接到服务器")
        
        # 创建请求消息
        request = self.protocol.create_request(method, params)
        
        # 创建 Future 等待响应
        future = asyncio.Future()
        self.pending_requests[request.id] = future
        
        try:
            # 发送请求
            message_data = self.protocol.serialize_message(request)
            await self.websocket.send(message_data)
            
            # 等待响应
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            # 清理超时的请求
            self.pending_requests.pop(request.id, None)
            raise asyncio.TimeoutError(f"请求超时: {method}")
        
        except Exception as e:
            # 清理失败的请求
            self.pending_requests.pop(request.id, None)
            raise e
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """发送通知"""
        if not self.websocket:
            raise ConnectionError("未连接到服务器")
        
        notification = self.protocol.create_notification(method, params)
        message_data = self.protocol.serialize_message(notification)
        await self.websocket.send(message_data)
    
    async def _message_loop(self):
        """消息处理循环"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            print("与服务器的连接已关闭")
        except Exception as e:
            print(f"消息循环出错: {e}")
    
    async def _handle_message(self, raw_message: str):
        """处理接收到的消息"""
        try:
            message_data = self.protocol.deserialize_message(raw_message)
            message = MCPMessage(**message_data)
            
            if message.type in ["response", "error"] and message.id:
                # 处理响应消息
                future = self.pending_requests.pop(message.id, None)
                if future and not future.done():
                    if message.type == "response":
                        future.set_result(message.result)
                    else:
                        error_msg = message.error.get("message", "Unknown error")
                        future.set_exception(Exception(error_msg))
            
            elif message.type == "notification":
                # 处理通知消息
                await self._handle_notification(message)
                
        except Exception as e:
            print(f"处理消息时出错: {e}")
    
    async def _handle_notification(self, message: MCPMessage):
        """处理通知消息"""
        # 客户端可以在这里处理来自服务器的通知
        print(f"收到通知: {message.method}, 参数: {message.params}")
    
    # 便捷方法示例
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return await self.send_request("model.info")
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        params = {"prompt": prompt, **kwargs}
        result = await self.send_request("model.generate", params)
        return result.get("text", "")
