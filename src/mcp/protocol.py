"""
MCP 协议实现
"""
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from enum import Enum


class MCPMessageType(str, Enum):
    """MCP 消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPMessage(BaseModel):
    """MCP 消息基类"""
    type: MCPMessageType
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    """MCP 错误"""
    code: int
    message: str
    data: Optional[Any] = None


class MCPProtocol:
    """MCP 协议处理器"""
    
    def __init__(self):
        """初始化协议处理器"""
        self.handlers: Dict[str, callable] = {}
        self.context: Dict[str, Any] = {}
    
    def register_handler(self, method: str, handler: callable):
        """注册方法处理器"""
        self.handlers[method] = handler
    
    def create_request(self, method: str, params: Optional[Dict[str, Any]] = None, 
                      message_id: Optional[str] = None) -> MCPMessage:
        """创建请求消息"""
        return MCPMessage(
            type=MCPMessageType.REQUEST,
            id=message_id or self._generate_id(),
            method=method,
            params=params
        )
    
    def create_response(self, request_id: str, result: Any) -> MCPMessage:
        """创建响应消息"""
        return MCPMessage(
            type=MCPMessageType.RESPONSE,
            id=request_id,
            result=result
        )
    
    def create_error(self, request_id: str, error: MCPError) -> MCPMessage:
        """创建错误消息"""
        return MCPMessage(
            type=MCPMessageType.ERROR,
            id=request_id,
            error=error.dict()
        )
    
    def create_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """创建通知消息"""
        return MCPMessage(
            type=MCPMessageType.NOTIFICATION,
            method=method,
            params=params
        )
    
    async def handle_message(self, message_data: Dict[str, Any]) -> Optional[MCPMessage]:
        """处理接收到的消息"""
        try:
            message = MCPMessage(**message_data)
            
            if message.type == MCPMessageType.REQUEST:
                return await self._handle_request(message)
            elif message.type == MCPMessageType.NOTIFICATION:
                await self._handle_notification(message)
                return None
            else:
                # 响应和错误消息通常由客户端处理
                return None
                
        except Exception as e:
            # 返回解析错误
            return self.create_error(
                request_id=message_data.get("id", "unknown"),
                error=MCPError(
                    code=-32700,
                    message="Parse error",
                    data=str(e)
                )
            )
    
    async def _handle_request(self, message: MCPMessage) -> MCPMessage:
        """处理请求消息"""
        method = message.method
        
        if method not in self.handlers:
            return self.create_error(
                request_id=message.id,
                error=MCPError(
                    code=-32601,
                    message="Method not found",
                    data=f"Method '{method}' is not supported"
                )
            )
        
        try:
            handler = self.handlers[method]
            result = await handler(message.params or {})
            return self.create_response(message.id, result)
            
        except Exception as e:
            return self.create_error(
                request_id=message.id,
                error=MCPError(
                    code=-32603,
                    message="Internal error",
                    data=str(e)
                )
            )
    
    async def _handle_notification(self, message: MCPMessage):
        """处理通知消息"""
        method = message.method
        
        if method in self.handlers:
            try:
                handler = self.handlers[method]
                await handler(message.params or {})
            except Exception as e:
                # 通知消息不返回错误
                print(f"处理通知时出错: {e}")
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return str(uuid.uuid4())
    
    def serialize_message(self, message: MCPMessage) -> str:
        """序列化消息"""
        return json.dumps(message.dict(exclude_none=True), ensure_ascii=False)
    
    def deserialize_message(self, data: str) -> Dict[str, Any]:
        """反序列化消息"""
        return json.loads(data)
