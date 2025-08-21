"""
MCP 协议实现
"""
import json
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)

class MCPMessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"

class MCPMessage(BaseModel):
    type: MCPMessageType
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class MCPError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class MCPProtocol:
    """MCP 协议处理器"""

    PARSE_ERROR = -32700
    METHOD_NOT_FOUND = -32601
    INTERNAL_ERROR = -32603

    def __init__(self):
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_handler(self, method: str, handler: Callable):
        self.handlers[method] = handler

    def register_handlers(self, mapping: Dict[str, Callable]):
        self.handlers.update(mapping)

    def create_request(self, method: str, params: Optional[Dict[str, Any]] = None,
                       message_id: Optional[str] = None) -> MCPMessage:
        return MCPMessage(
            type=MCPMessageType.REQUEST,
            id=message_id or self._generate_id(),
            method=method,
            params=params
        )

    def create_response(self, request_id: str, result: Any) -> MCPMessage:
        return MCPMessage(
            type=MCPMessageType.RESPONSE,
            id=request_id,
            result=result
        )

    def create_error(self, request_id: str, error: MCPError) -> MCPMessage:
        return MCPMessage(
            type=MCPMessageType.ERROR,
            id=request_id,
            error=error.dict()
        )

    def create_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        return MCPMessage(
            type=MCPMessageType.NOTIFICATION,
            method=method,
            params=params
        )

    async def handle_message(self, message_data: Dict[str, Any]) -> Optional[MCPMessage]:
        try:
            message = MCPMessage(**message_data)
            if message.type == MCPMessageType.REQUEST:
                return await self._handle_request(message)
            if message.type == MCPMessageType.NOTIFICATION:
                await self._handle_notification(message)
                return None
            return None
        except Exception as e:
            logger.exception("解析消息失败")
            return self.create_error(
                request_id=message_data.get("id", "unknown"),
                error=MCPError(code=self.PARSE_ERROR, message="Parse error", data=str(e))
            )

    async def _handle_request(self, message: MCPMessage) -> MCPMessage:
        method = message.method
        if not method or method not in self.handlers:
            return self.create_error(
                request_id=message.id,
                error=MCPError(
                    code=self.METHOD_NOT_FOUND,
                    message="Method not found",
                    data=f"Method '{method}' is not supported"
                )
            )
        try:
            handler = self.handlers[method]
            result = handler(message.params or {})  # 可支持同步或异步
            if hasattr(result, "__await__"):
                result = await result
            return self.create_response(message.id, result)
        except Exception as e:
            logger.exception("处理请求出错: %s", method)
            return self.create_error(
                request_id=message.id,
                error=MCPError(
                    code=self.INTERNAL_ERROR,
                    message="Internal error",
                    data=str(e)
                )
            )

    async def _handle_notification(self, message: MCPMessage):
        method = message.method
        if method in self.handlers:
            try:
                maybe = self.handlers[method](message.params or {})
                if hasattr(maybe, "__await__"):
                    await maybe
            except Exception as e:
                logger.error("通知处理失败 %s: %s", method, e)

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def serialize_message(self, message: MCPMessage) -> str:
        return json.dumps(message.dict(exclude_none=True), ensure_ascii=False)

    def deserialize_message(self, data: str) -> Dict[str, Any]:
        return json.loads(data)